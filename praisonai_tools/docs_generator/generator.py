"""
Reference Documentation Generator for PraisonAI.

Generates Mintlify-compatible MDX documentation from Python and TypeScript source code.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import ast
import re
import json


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ParamInfo:
    name: str
    type: str = "Any"
    default: Optional[str] = None
    description: str = ""
    required: bool = True


@dataclass
class MethodInfo:
    name: str
    signature: str = ""
    return_type: str = "None"
    return_description: str = ""
    docstring: str = ""
    params: List[ParamInfo] = field(default_factory=list)
    raises: List[Tuple[str, str]] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    is_async: bool = False
    is_static: bool = False
    is_classmethod: bool = False


@dataclass
class ClassInfo:
    name: str
    docstring: str = ""
    bases: List[str] = field(default_factory=list)
    init_params: List[ParamInfo] = field(default_factory=list)
    methods: List[MethodInfo] = field(default_factory=list)
    class_methods: List[MethodInfo] = field(default_factory=list)
    properties: List[ParamInfo] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


@dataclass
class FunctionInfo:
    name: str
    signature: str = ""
    return_type: str = "None"
    return_description: str = ""
    docstring: str = ""
    params: List[ParamInfo] = field(default_factory=list)
    raises: List[Tuple[str, str]] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    is_async: bool = False


@dataclass
class ModuleInfo:
    name: str  # fully qualified, e.g., praisonaiagents.agent.agent
    short_name: str  # e.g., agent
    docstring: Optional[str] = None
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    constants: List[Tuple[str, str]] = field(default_factory=list)
    is_init: bool = False
    package: str = "python"
    
    @property
    def display_name(self) -> str:
        # For __init__.py files, show the package name, not __init__
        if self.name.endswith(".__init__"):
            return self.name.rsplit(".", 1)[0]
        return self.name


class LayoutType(Enum):
    LEGACY = "legacy"        # Consistently in one file per module
    GRANULAR = "granular"    # Three Pillars (Modules, Classes, Functions)


# =============================================================================
# UTILS
# =============================================================================

def sanitize_type_for_mdx(type_str: Optional[str]) -> Optional[str]:
    """Sanitize complex type annotations for MDX compatibility."""
    if not type_str:
        return type_str
    
    result = type_str.strip()
    result = re.sub(r"'([A-Z][a-zA-Z0-9_]*)'", r"\1", result)
    
    while "[[" in result or " Union[" in result or " Optional[" in result:
        new_result = re.sub(r"\[\[(.*?)\]\]", r"[\1]", result)
        if new_result == result:
            break
        result = new_result
        
    if "[" in result:
        return result.split("[")[0]
        
    return result


def escape_mdx(text: str) -> str:
    """Escape text for MDX compatibility."""
    if not text:
        return text
        
    code_blocks = []
    def save_code_block(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks)-1}__"
    
    text = re.sub(r"```.*?```", save_code_block, text, flags=re.DOTALL)
    text = re.sub(r"`.*?`", save_code_block, text)
    
    text = text.replace('{', '&#123;').replace('}', '&#125;')
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    
    for i, block in enumerate(code_blocks):
        text = text.replace(f"__CODE_BLOCK_{i}__", block)
        
    return text


def validate_mdx(content: str) -> List[str]:
    """Validate MDX content for common issues."""
    errors = []
    lines = content.split('\n')
    in_code_block = False
    in_frontmatter = False
    frontmatter_count = 0
    
    VALID_MDX_TAGS = {
        'div', 'span', 'p', 'a', 'br', 'hr', 'img', 'ul', 'ol', 'li', 
        'table', 'tr', 'td', 'th', 'thead', 'tbody', 'code', 'pre',
        'strong', 'em', 'b', 'i', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'Card', 'CardGroup', 'Note', 'Warning', 'Info', 'Tip', 'Check',
        'Danger', 'Accordion', 'AccordionGroup', 'Tab', 'Tabs', 'Step',
        'Steps', 'Frame', 'Icon', 'Badge', 'Tooltip', 'CodeGroup',
        'Expandable', 'ParamField', 'ResponseField', 'Columns', 'Column',
        'RequestExample', 'ResponseExample', 'Banner', 'Update', 'View',
        'Tree', 'Tile', 'Tiles', 'Panel', 'Color'
    }

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if stripped == '---':
            frontmatter_count += 1
            in_frontmatter = frontmatter_count == 1
            if frontmatter_count == 2:
                in_frontmatter = False
            continue
        
        if in_frontmatter:
            continue
        
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            continue
        
        if in_code_block:
            continue
        
        angle_matches = re.findall(r'(?<!`)(<[a-zA-Z_][a-zA-Z0-9_]*>)(?!`)', line)
        for match in angle_matches:
            tag = match[1:-1]
            if tag not in VALID_MDX_TAGS and tag.lower() not in {t.lower() for t in VALID_MDX_TAGS if t.islower()}:
                errors.append(f"Line {i}: Unescaped JSX-like tag: {match}")
        
        curly_matches = re.findall(r'(?<!`)(?<!=)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!`)', line)
        for match in curly_matches:
            errors.append(f"Line {i}: Unescaped JSX expression: {{{match}}}")
    
    return errors


def escape_for_table(text: str, is_type: bool = False) -> str:
    """Escape text for use in markdown tables."""
    if not text:
        return text
    
    if is_type:
        text = sanitize_type_for_mdx(text) or text
        
    text = text.replace('|', '\\|')
    # Use HTML entities for angle brackets to avoid tag confusion
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    
    return text


def sanitize_description(text: str, max_length: int = 150) -> str:
    """Sanitize description for YAML frontmatter. Truncates at word boundary."""
    if not text:
        return ""
    
    first_line = text.split('\n')[0].strip()
    first_line = first_line.replace('"', "'")
    first_line = re.sub(r'[<>{}]', '', first_line)
    
    if len(first_line) > max_length:
        # Truncate at word boundary
        truncated = first_line[:max_length].rsplit(' ', 1)[0]
        first_line = truncated + "..."
    
    return first_line


# Abbreviations to preserve in uppercase for SEO
SEO_ABBREVIATIONS = {"llm", "api", "cli", "id", "url", "http", "ai", "a2a", "mcp", "rag", "os", "db", "gui", "io"}

def friendly_title(name: str, page_type: str = "class") -> str:
    """Convert a code name to a friendly, SEO-optimized title.
    
    Examples:
        audio_agent -> Audio Agent
        AfterAgentInput -> After Agent Input
        BaseLLM -> Base LLM
    """
    if not name:
        return name
    
    # Convert snake_case to Title Case
    if "_" in name:
        parts = name.split("_")
        titled_parts = []
        for part in parts:
            if part.lower() in SEO_ABBREVIATIONS:
                titled_parts.append(part.upper())
            else:
                titled_parts.append(part.capitalize())
        return " ".join(titled_parts)
    
    # Convert PascalCase/camelCase to Title Case with spaces
    result = []
    current_word = []
    
    for i, char in enumerate(name):
        if char.isupper():
            if current_word:
                word = "".join(current_word)
                if word.lower() in SEO_ABBREVIATIONS:
                    result.append(word.upper())
                else:
                    result.append(word)
                current_word = []
            current_word.append(char)
        else:
            current_word.append(char)
    
    # Don't forget the last word
    if current_word:
        word = "".join(current_word)
        if word.lower() in SEO_ABBREVIATIONS:
            result.append(word.upper())
        else:
            result.append(word)
    
    # Join and fix spaced abbreviations (L L M -> LLM)
    title = " ".join(result)
    for abbr in SEO_ABBREVIATIONS:
        spaced = " ".join(abbr.upper())
        if spaced in title:
            title = title.replace(spaced, abbr.upper())
    
    return title


# =============================================================================
# CONFIGURATION
# =============================================================================

SKIP_MODULES = {
    "__pycache__", "_config", "_lazy", "_logging", "_warning_patch", 
    "_resolver_helpers", "audit", "lite", "profiling", "utils", "__init__",
    "_dev", "test", "tests", "__main__", "setup", ".ipynb_checkpoints"
}
SKIP_METHODS = {
    "to_dict", "from_dict", "to_json", "from_json", "to_yaml", "from_yaml",
    "copy", "dict", "json", "__init__", "__call__", "__str__", "__repr__",
    "model_dump", "model_validate", "model_json_schema", "__post_init__",
    "__enter__", "__exit__", "__iter__", "__len__", "__getitem__", "__setitem__"
}

ICON_MAP = {
    # Core Components
    "agent": "robot",
    "agents": "users",
    "task": "list-check",
    "process": "diagram-project",
    "tools": "wrench",
    "knowledge": "book-open",
    "memory": "brain",
    "llm": "microchip",
    "rag": "magnifying-glass",
    "embeddings": "vector-square",
    "observability": "eye",
    "planning": "brain-circuit",
    "handoff": "handshake",
    "approval": "check-double",
    "guardrails": "shield-halved",
    "config": "gear",
    "session": "clock-rotate-left",
    "storage": "database",
    "skills": "bolt",
    "workflows": "route",
    "telemetry": "chart-line",
    "search": "magnifying-glass",
    
    # Modules & Integration
    "a2a": "network-wired",
    "agui": "window-maximize",
    "bus": "bus",
    "chunking": "scissors",
    "compaction": "compress",
    "background": "layer-group",
    "embedding": "layer-group",
    "embed": "layer-group",
    "escalation": "arrow-trend-up",
    "eval": "gauge",
    "flow_display": "diagram-project",
    "dimensions": "ruler-combined",
    "feature_configs": "sliders",
    "param_resolver": "code-fork",
    "parse_utils": "file-magnifying-glass",
    "presets": "bookmark",
    "main": "house",
    "index": "house",
    "server": "server",
    "mcp_server": "server",
    "acp": "server",
    "adapters": "plug",
    "api": "code",
    "lsp": "code",
    "auto": "magic",
    "browser": "globe",
    "public": "globe",
    "deploy": "cloud-arrow-up",
    "upload_vision": "upload",
    "train_vision": "eye",
    "obs": "eye",
    "ai": "brain",
    "context": "brain",
    "cache": "database",
    "db": "database",
    "base": "database",
    "events": "bell",
    "output": "file-export",
    "models": "box",
    "result": "square-check",
    "retrieval_config": "gears",
    "manager": "users-gear",
    "types": "tags",
    "version": "tag",
    "inc": "plus",
    "video": "video",
    "video_agent": "video",
    "audio_agent": "microphone",
    "ocr_agent": "file-lines",
    "image_agent": "image",
    "agent_scheduler": "calendar-day",
    "agents_generator": "wand-magic-sparkles",
    "decorator": "wand-magic-sparkles",
    "utils": "screwdriver-wrench",
    "default": "file-code",
    
    # Rust-specific
    "derive": "wand-magic-sparkles",
    "cli": "terminal",
    "crate": "cube",
    "error": "circle-exclamation",
    "prelude": "star",
    "builder": "hammer",
}

def get_icon_for_module(module_name: str) -> str:
    """Get the icon name for a module."""
    module_name = module_name.lower()
    
    if module_name in ICON_MAP:
        return ICON_MAP[module_name]
    
    if "agent" in module_name: return ICON_MAP["agent"]
    if "tool" in module_name: return ICON_MAP["tool"]
    if "task" in module_name: return ICON_MAP["task"]
    if "llm" in module_name: return ICON_MAP["llm"]
    if "config" in module_name: return ICON_MAP["config"]
    if "memory" in module_name: return ICON_MAP["memory"]
    if "knowledge" in module_name: return ICON_MAP["knowledge"]
    
    return ICON_MAP["default"]


# =============================================================================
# PARSERS
# =============================================================================

class PythonDocParser:
    """Parse Python source code using ast."""
    
    def __init__(self, package_path: Path, package_name: str):
        self.package_path = package_path
        self.package_name = package_name
        self._lazy_imports: Dict[str, Tuple[str, str]] = {}
        self._load_lazy_imports()
    
    def _load_lazy_imports(self):
        """Load _LAZY_IMPORTS and _LAZY_GROUPS from all __init__.py files.
        
        Recursively scans the package and all submodules for lazy import patterns.
        Supports two patterns:
        1. _LAZY_IMPORTS: flat dict of symbol -> (module, symbol)
        2. _LAZY_GROUPS: nested dict of group -> {symbol: (module, symbol)}
        """
        # Scan all __init__.py files in the package
        init_files = list(self.package_path.rglob("__init__.py"))
        
        for init_file in init_files:
            try:
                content = init_file.read_text()
                self._parse_lazy_patterns(content)
            except Exception:
                pass
    
    def _parse_lazy_patterns(self, content: str):
        """Parse various lazy loading patterns from file content.
        
        Supports patterns:
        1. _LAZY_IMPORTS: flat dict of symbol -> (module, symbol)
        2. _LAZY_GROUPS: nested dict of group -> {symbol: (module, symbol)}
        3. TOOL_MAPPINGS: dict of symbol -> (module, class_or_none)
        4. __all__: explicit export list (fallback for inline __getattr__)
        """
        # Pattern 1: _LAZY_IMPORTS (flat dict)
        match = re.search(r'_LAZY_IMPORTS\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', content, re.DOTALL)
        if match:
            dict_content = match.group(1)
            pattern = r"'(\w+)':\s*\('([^']+)',\s*'([^']+)'\)"
            for m in re.finditer(pattern, dict_content):
                self._lazy_imports[m.group(1)] = (m.group(2), m.group(3))
        
        # Pattern 2: _LAZY_GROUPS (nested dict used by hooks, etc.)
        match = re.search(r'_LAZY_GROUPS\s*=\s*\{(.+?)\n\}', content, re.DOTALL)
        if match:
            groups_content = match.group(1)
            # Parse all symbol -> (module, symbol) pairs within groups
            pattern = r"'(\w+)':\s*\('([^']+)',\s*'([^']+)'\)"
            for m in re.finditer(pattern, groups_content):
                symbol_name = m.group(1)
                module_path = m.group(2)
                self._lazy_imports[symbol_name] = (module_path, symbol_name)
        
        # Pattern 3: TOOL_MAPPINGS (used by tools/__init__.py)
        match = re.search(r'TOOL_MAPPINGS\s*=\s*\{(.+?)\n\}', content, re.DOTALL)
        if match:
            mappings_content = match.group(1)
            # Parse 'symbol': ('.module', None) or 'symbol': ('.module', 'ClassName')
            pattern = r"'(\w+)':\s*\('([^']+)',\s*(?:None|'([^']*)')\)"
            for m in re.finditer(pattern, mappings_content):
                symbol_name = m.group(1)
                self._lazy_imports[symbol_name] = (m.group(2), symbol_name)



    
    def get_modules(self) -> List[str]:
        """Get list of modules to document."""
        modules = set()
        for symbol, (module_path, _) in self._lazy_imports.items():
            modules.add(module_path)
        
        for item in self.package_path.iterdir():
            if item.is_dir() and item.name not in SKIP_MODULES and not item.name.startswith('_'):
                modules.add(f"{self.package_name}.{item.name}")
            elif item.is_file() and item.suffix == '.py' and item.stem not in SKIP_MODULES and not item.stem.startswith('_'):
                modules.add(f"{self.package_name}.{item.stem}")
        
        return sorted(modules)
    
    def parse_module(self, module_path: str) -> Optional[ModuleInfo]:
        """Parse a module using ast."""
        try:
            rel_path = module_path.replace(f"{self.package_name}.", "").replace(".", "/")
            file_path = self.package_path / f"{rel_path}.py"
            
            if not file_path.exists():
                file_path = self.package_path / rel_path / "__init__.py"
                if not file_path.exists():
                    return None
            
            source = file_path.read_text()
            tree = ast.parse(source)
            
            module_short_name = module_path.split(".")[-1]
            info = ModuleInfo(
                name=module_path,
                short_name=module_short_name,
                docstring=ast.get_docstring(tree) or "",
                is_init=file_path.name == "__init__.py"
            )
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                    class_info = self._parse_class(node)
                    if class_info: info.classes.append(class_info)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                    func_info = self._parse_function(node)
                    if func_info: info.functions.append(func_info)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            info.constants.append((target.id, self._get_value(node.value)))
            
            return info
        except Exception:
            return None
    
    def _parse_class(self, node: ast.ClassDef) -> Optional[ClassInfo]:
        try:
            bases = [self._get_annotation(b) for b in node.bases]
            raw_doc = ast.get_docstring(node) or ""
            parsed_doc = self._parse_docstring(raw_doc)
            
            info = ClassInfo(
                name=node.name, 
                docstring=parsed_doc["description"],
                bases=bases,
                examples=parsed_doc["examples"]
            )
            
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name == "__init__":
                        info.init_params = self._parse_params(item)
                    elif not item.name.startswith("_"):
                        method = self._parse_method(item)
                        if method:
                            if method.is_classmethod: info.class_methods.append(method)
                            else: info.methods.append(method)
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    if not item.target.id.startswith("_"):
                        info.properties.append(ParamInfo(
                            name=item.target.id,
                            type=self._get_annotation(item.annotation),
                        ))
            return info
        except Exception:
            return None
    
    def _parse_method(self, node) -> Optional[MethodInfo]:
        try:
            is_async = isinstance(node, ast.AsyncFunctionDef)
            is_static = any(isinstance(d, ast.Name) and d.id == 'staticmethod' for d in node.decorator_list)
            is_classmethod = any(isinstance(d, ast.Name) and d.id == 'classmethod' for d in node.decorator_list)
            
            raw_doc = ast.get_docstring(node) or ""
            parsed_doc = self._parse_docstring(raw_doc)
            
            params = self._parse_params(node)
            # Merge descriptions from docstring into ParamInfo
            for p in params:
                if p.name in parsed_doc["args"]:
                    p.description = parsed_doc["args"][p.name]
            
            sig_parts = [f"{p.name}: {p.type}" for p in params]
            
            return MethodInfo(
                name=node.name,
                signature=", ".join(sig_parts),
                return_type=self._get_annotation(node.returns) or parsed_doc["returns_type"] or "None",
                return_description=parsed_doc["returns"],
                docstring=parsed_doc["description"],
                params=params,
                raises=parsed_doc["raises"],
                examples=parsed_doc["examples"],
                is_async=is_async,
                is_static=is_static,
                is_classmethod=is_classmethod,
            )
        except Exception:
            return None
    
    def _parse_function(self, node) -> Optional[FunctionInfo]:
        try:
            is_async = isinstance(node, ast.AsyncFunctionDef)
            raw_doc = ast.get_docstring(node) or ""
            parsed_doc = self._parse_docstring(raw_doc)
            
            params = self._parse_params(node)
            # Merge descriptions from docstring into ParamInfo
            for p in params:
                if p.name in parsed_doc["args"]:
                    p.description = parsed_doc["args"][p.name]
            
            sig_parts = [f"{p.name}: {p.type}" for p in params]
            
            return FunctionInfo(
                name=node.name,
                signature=", ".join(sig_parts),
                return_type=self._get_annotation(node.returns) or parsed_doc["returns_type"] or "None",
                return_description=parsed_doc["returns"],
                docstring=parsed_doc["description"],
                params=params,
                raises=parsed_doc["raises"],
                examples=parsed_doc["examples"],
                is_async=is_async,
            )
        except Exception:
            return None
    
    def _parse_docstring(self, docstring: str) -> Dict[str, Any]:
        """Parse Google-style docstring into sections."""
        result = {
            "description": "",
            "args": {},
            "returns": "",
            "returns_type": "",
            "raises": [],
            "examples": []
        }
        
        if not docstring:
            return result
        
        # More robust splitting: only match sections at the start of original lines
        # This prevents picking up 'Examples:' inside an 'Args' description
        section_pattern = r'\n\s*(Args|Parameters|Returns|Raises|Example|Examples|Usage):?\s*\n'
        sections = re.split(section_pattern, '\n' + docstring)
        result["description"] = sections[0].strip()
        
        for i in range(1, len(sections), 2):
            section_name = sections[i].lower()
            section_content = sections[i+1]
            
            if section_name in ("args", "parameters"):
                arg_pattern = r'^\s*(\w+)(?:\s*\(([^)]+)\))?:\s*(.+)$'
                current_arg = None
                for line in section_content.split('\n'):
                    match = re.match(arg_pattern, line)
                    if match:
                        current_arg = match.group(1)
                        desc = match.group(3)
                        result["args"][current_arg] = desc
                    elif current_arg and line.strip() and (line.startswith(' ') or line.startswith('\t')):
                        result["args"][current_arg] += " " + line.strip()
            
            elif section_name == "returns":
                ret_match = re.match(r'^\s*([^:]+):\s*(.+)$', section_content, re.DOTALL)
                if ret_match:
                    result["returns_type"] = ret_match.group(1).strip()
                    result["returns"] = ret_match.group(2).strip()
                else:
                    result["returns"] = section_content.strip()
            
            elif section_name == "raises":
                raises_lines = section_content.split('\n')
                for line in raises_lines:
                    match = re.match(r'^\s*(\w+):\s*(.+)$', line)
                    if match:
                        result["raises"].append((match.group(1), match.group(2)))
            
            elif section_name in ("example", "examples", "usage"):
                content = section_content.strip()
                # Strip existing triple backticks if they wrap the entire example
                content = re.sub(r'^```[a-z]*\n?(.*?)\n?```$', r'\1', content, flags=re.DOTALL)
                result["examples"].append(content.strip())
                
        return result
    
    def _parse_params(self, node) -> List[ParamInfo]:
        params = []
        defaults = node.args.defaults
        num_defaults = len(defaults)
        num_args = len(node.args.args)
        
        for i, arg in enumerate(node.args.args):
            if arg.arg in ("self", "cls"):
                continue
            
            default_idx = i - (num_args - num_defaults)
            has_default = default_idx >= 0
            default_val = None
            if has_default:
                default_val = self._get_value(defaults[default_idx])
            
            params.append(ParamInfo(
                name=arg.arg,
                type=self._get_annotation(arg.annotation),
                default=default_val,
                required=not has_default,
            ))
        
        return params
    
    def _get_annotation(self, node) -> str:
        if node is None: return "Any"
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Constant): return repr(node.value)
        try:
            return ast.unparse(node)
        except Exception:
            return "Any"
    
    def _get_value(self, node) -> str:
        if node is None: return "None"
        if isinstance(node, ast.Constant): return repr(node.value)
        try:
            return ast.unparse(node)
        except Exception:
            return "..."


class TypeScriptDocParser:
    """Parse TypeScript source code for documentation."""
    
    def __init__(self, source_path: Path):
        self.source_path = source_path
    
    def get_modules(self) -> List[str]:
        """Get list of modules from directory structure."""
        modules = []
        for item in self.source_path.iterdir():
            if item.is_dir() and item.name not in SKIP_MODULES and not item.name.startswith('_'):
                modules.append(item.name)
        return sorted(modules)
    
    def parse_module(self, module_name: str) -> Optional[ModuleInfo]:
        """Parse a TypeScript module."""
        module_path = self.source_path / module_name
        index_file = module_path / "index.ts"
        
        if not index_file.exists():
            single_file = self.source_path / f"{module_name}.ts"
            if single_file.exists():
                index_file = single_file
            else:
                return None
        
        try:
            content = index_file.read_text()
            module_short_name = module_name
            info = ModuleInfo(
                name=f"praisonai.{module_name}",
                short_name=module_short_name,
                docstring=self._extract_module_doc(content),
                package="typescript",
            )
            info.classes = self._parse_classes(content)
            info.functions = self._parse_functions(content)
            return info
        except Exception:
            return None
    
    def _extract_module_doc(self, content: str) -> str:
        match = re.search(r'^/\*\*\s*(.*?)\s*\*/', content, re.DOTALL)
        if match:
            doc = match.group(1)
            doc = re.sub(r'\n\s*\*\s*', '\n', doc)
            doc = re.sub(r'@\w+.*', '', doc)
            return doc.strip()
        return ""
    
    def _parse_classes(self, content: str) -> List[ClassInfo]:
        classes = []
        pattern = r'export\s+(?:class|interface)\s+(\w+)(?:\s+extends\s+(\w+))?'
        for match in re.finditer(pattern, content):
            name = match.group(1)
            base = match.group(2)
            classes.append(ClassInfo(
                name=name,
                bases=[base] if base else [],
                docstring=f"TypeScript {name} class",
            ))
        return classes
    
    def _parse_functions(self, content: str) -> List[FunctionInfo]:
        functions = []
        pattern = r'export\s+(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^{]+))?'
        for match in re.finditer(pattern, content):
            name = match.group(1)
            params_str = match.group(2)
            return_type = match.group(3) or "void"
            functions.append(FunctionInfo(
                name=name,
                signature=params_str.strip(),
                return_type=return_type.strip(),
                is_async='async' in match.group(0),
            ))
        return functions


# =============================================================================
# GENERATOR
# =============================================================================

class MDXGenerator:
    """Generate MDX documentation files."""
    
    def __init__(self, output_dir: Path, package_name: str, config: Dict[str, Any], layout: LayoutType = LayoutType.LEGACY):
        self.output_dir = output_dir
        self.package_name = package_name
        self.config = config
        self.layout = layout
        self.generated_files = set()  # Use set for faster lookups and cleanup
    
    def generate_module_doc(self, info: ModuleInfo, dry_run: bool = False) -> List[Path]:
        """Generate MDX documentation for a module (potentially multiple files)."""
        if self.layout == LayoutType.LEGACY:
            return self._generate_legacy(info, dry_run)
        else:
            return self._generate_granular(info, dry_run)

    def _generate_legacy(self, info: ModuleInfo, dry_run: bool = False) -> List[Path]:
        """Original single-file generation."""
        try:
            output_file = self.output_dir / f"{info.short_name}.mdx"
            content = self._render_module(info)
            if not dry_run:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(content)
                self._track_file(output_file)
            return [output_file]
        except Exception:
            return []

    def _generate_granular(self, info: ModuleInfo, dry_run: bool = False) -> List[Path]:
        """New multi-file generation (Three Pillars)."""
        generated = []
        try:
            # 1. Module Page (Index)
            module_file = self.output_dir / "modules" / f"{info.short_name}.mdx"
            module_content = self._render_module_granular(info)
            if not dry_run:
                module_file.parent.mkdir(parents=True, exist_ok=True)
                module_file.write_text(module_content)
                self._track_file(module_file)
            generated.append(module_file)

            # 2. Class Pages
            for cls in info.classes:
                class_file = self.output_dir / "classes" / f"{cls.name}.mdx"
                class_content = self._render_class_page(cls, info)
                if not dry_run:
                    class_file.parent.mkdir(parents=True, exist_ok=True)
                    class_file.write_text(class_content)
                    self._track_file(class_file)
                generated.append(class_file)

                # 2. Class Methods (as separate function pages)
                for m in cls.class_methods:
                    if m.name in SKIP_METHODS:
                        continue
                    method_file = self.output_dir / "functions" / f"{cls.name}-{m.name}.mdx"
                    method_content = self._render_function_page(m, info, cls_name=cls.name)
                    if not dry_run:
                        method_file.parent.mkdir(parents=True, exist_ok=True)
                        method_file.write_text(method_content)
                        self._track_file(method_file)
                    generated.append(method_file)

                # 3. Instance Methods (as separate function pages)
                for m in cls.methods:
                    if m.name in SKIP_METHODS:
                        continue
                    method_file = self.output_dir / "functions" / f"{cls.name}-{m.name}.mdx"
                    method_content = self._render_function_page(m, info, cls_name=cls.name)
                    if not dry_run:
                        method_file.parent.mkdir(parents=True, exist_ok=True)
                        method_file.write_text(method_content)
                        self._track_file(method_file)
                    generated.append(method_file)

            # 4. Top-level Functions
            for func in info.functions:
                func_file = self.output_dir / "functions" / f"{func.name}.mdx"
                func_content = self._render_function_page(func, info)
                if not dry_run:
                    func_file.parent.mkdir(parents=True, exist_ok=True)
                    func_file.write_text(func_content)
                    self._track_file(func_file)
                generated.append(func_file)

        except Exception as e:
            print(f"Error generating granular: {e}")
        return generated

    def _track_file(self, path: Path):
        docs_root = Path("/Users/praison/PraisonAIDocs")
        rel_path = str(path.relative_to(docs_root))
        nav_path = rel_path.replace('.mdx', '').replace('\\', '/')
        self.generated_files.add(nav_path)
    
    def _render_module(self, info: ModuleInfo) -> str:
        safe_docstring = escape_mdx(info.docstring) if info.docstring else ""
        desc = sanitize_description(info.docstring) or f"API reference for {info.short_name}"
        badge_color = self.config.get("badge_color", "gray")
        badge_text = self.config.get("badge_text", "Module")
        title_suffix = self.config.get("title_suffix", "")
        
        lines = [
            "---",
            f'title: "{friendly_title(info.short_name, "module")}{title_suffix}"',
            f'sidebarTitle: "{friendly_title(info.short_name, "module")}"',
            f'description: "{desc}"',
            f'icon: "{get_icon_for_module(info.short_name)}"',
            "---",
            "",
            f"# {info.short_name}",
            "",
            f'<Badge color="{badge_color}">{badge_text}</Badge>',
            "",
            safe_docstring,
            "",
            "## Import",
            "",
        ]
        
        # Language-specific import syntax
        if info.package == "rust":
            lines.extend([
                "```rust",
                f"use {info.name.replace('.', '::')}::*;",
                "```",
                "",
            ])
        else:
            lines.extend([
                "```python",
                f"from {info.name.rsplit('.', 1)[0] if '.' in info.name else info.name} import {info.short_name}",
                "```",
                "",
            ])

        if info.classes:
            lines.append("## Classes\n")
            for cls in info.classes:
                lines.extend(self._render_class(cls, info.package))
                lines.append("")

        if info.functions:
            lines.append("## Functions\n")
            for func in info.functions:
                lines.extend(self._render_function(func, info.package))
                lines.append("")

        if info.constants:
            lines.extend([
                "## Constants",
                "",
                "| Name | Value |",
                "|------|-------|",
            ])
            for name, value in info.constants:
                val_str = str(value)
                truncated_val = val_str[:200]
                if len(val_str) > 200:
                    truncated_val += "..."
                lines.append(f"| `{name}` | `{escape_for_table(truncated_val, is_type=False)}` |")
            lines.append("")
        
        return "\n".join(lines)

    def _render_module_granular(self, info: ModuleInfo) -> str:
        """Render the Module Index page for granular layout with full info."""
        safe_docstring = escape_mdx(info.docstring) if info.docstring else ""
        desc = sanitize_description(info.docstring) or f"Module reference for {info.short_name}"
        badge_color = self.config.get("badge_color", "gray")
        badge_text = self.config.get("badge_text", "Module")
        title_suffix = self.config.get("title_suffix", "")
        
        lines = [
            "---",
            f'title: "{friendly_title(info.short_name, "module")}{title_suffix}"',
            f'sidebarTitle: "{friendly_title(info.short_name, "module")}"',
            f'description: "{desc}"',
            f'icon: "{get_icon_for_module(info.short_name)}"',
            "---",
            "",
            f"# {info.short_name}",
            "",
            f'<Badge color="{badge_color}">{badge_text}</Badge>',
            "",
            safe_docstring,
            "",
        ]
        
        # Add import section with language-specific syntax
        lines.append("## Import")
        lines.append("")
        if info.package == "rust":
            lines.append("```rust")
            lines.append(f"use {info.name.replace('.', '::')}::*;")
            lines.append("```")
        elif info.package == "typescript":
            lines.append("```typescript")
            lines.append(f"import {{ {info.short_name} }} from 'praisonai';")
            lines.append("```")
        else:
            lines.append("```python")
            lines.append(f"from {info.name.rsplit('.', 1)[0] if '.' in info.name else info.name} import {info.short_name}")
            lines.append("```")
        lines.append("")

        if info.classes:
            lines.append("## Classes\n")
            lines.append("<CardGroup cols={2}>")
            for cls in info.classes:
                lines.append(f'  <Card title="{cls.name}" icon="brackets-curly" href="../classes/{cls.name}">')
                cls_desc = sanitize_description(cls.docstring) or "Class definition."
                lines.append(f"    {cls_desc}")
                lines.append("  </Card>")
            lines.append("</CardGroup>\n")

        if info.functions:
            visible_functions = [f for f in info.functions if f.name not in SKIP_METHODS]
            if visible_functions:
                lines.append("## Functions\n")
                lines.append("<CardGroup cols={2}>")
                for func in visible_functions:
                    lines.append(f'  <Card title="{func.name}()" icon="function" href="../functions/{func.name}">')
                    func_desc = sanitize_description(func.docstring) or "Function definition."
                    lines.append(f"    {func_desc}")
                    lines.append("  </Card>")
                lines.append("</CardGroup>\n")

        if info.constants:
            lines.extend([
                "### Constants",
                "",
                "| Name | Value |",
                "|------|-------|",
            ])
            for name, value in info.constants:
                val_str = str(value)
                truncated_val = val_str[:200]
                if len(val_str) > 200:
                    truncated_val += "..."
                lines.append(f"| `{name}` | `{escape_for_table(truncated_val, is_type=False)}` |")
            lines.append("")
        
        return "\n".join(lines)

    def _render_class_page(self, cls: ClassInfo, module_info: ModuleInfo) -> str:
        """Render a dedicated Class Blueprint page."""
        safe_docstring = escape_mdx(cls.docstring) if cls.docstring else ""
        desc = sanitize_description(cls.docstring) or f"Class reference for {cls.name}"
        badge_color = self.config.get("badge_color", "gray")
        badge_text = self.config.get("badge_text", "Module")
        title_suffix = self.config.get("title_suffix", "")
        is_rust = module_info.package == "rust"
        lang = "rust" if is_rust else "python"
        
        lines = [
            "---",
            f'title: "{friendly_title(cls.name, "class")}{title_suffix}"',
            f'sidebarTitle: "{friendly_title(cls.name, "class")}"',
            f'description: "{cls.name}: {desc}"',
            'icon: "brackets-curly"',
            "---",
            "",
            f"# {cls.name}",
            "",
            f"> Defined in the [**{friendly_title(module_info.short_name, 'module')}**](../modules/{module_info.short_name}) module.",
            "",
            f'<Badge color="{badge_color}">{badge_text}</Badge>',
            "",
            safe_docstring,
            "",
        ]

        # Add Mermaid Diagram if applicable
        mermaid = self._render_mermaid_diagram(cls.name)
        if mermaid:
            lines.append(mermaid)
            lines.append("")

        # For Rust: show Fields (properties) first, then Methods inline
        if is_rust:
            if cls.properties:
                lines.append("## Fields\n")
                lines.append("| Name | Type | Description |")
                lines.append("|------|------|-------------|")
                for p in cls.properties:
                    p_type = escape_mdx(p.type) if p.type else "-"
                    p_desc = escape_mdx(p.description)[:80] if p.description else "-"
                    lines.append(f"| `{p.name}` | `{p_type}` | {p_desc} |")
                lines.append("")
            
            if cls.methods:
                visible_methods = [m for m in cls.methods if m.name not in SKIP_METHODS]
                if visible_methods:
                    lines.append("## Methods\n")
                    for m in visible_methods:
                        async_prefix = "async " if getattr(m, 'is_async', False) else ""
                        ret_type = m.return_type if m.return_type else "()"
                        lines.append(f"### `{m.name}`\n")
                        lines.append(f"```rust\n{async_prefix}fn {m.name}({m.signature}) -> {ret_type}\n```\n")
                        if m.docstring:
                            lines.append(escape_mdx(m.docstring))
                            lines.append("")
                        if m.params:
                            lines.append("**Parameters:**\n")
                            lines.append("| Name | Type |")
                            lines.append("|------|------|")
                            for p in m.params:
                                p_type = escape_mdx(p.type) if p.type else "-"
                                lines.append(f"| `{p.name}` | `{p_type}` |")
                            lines.append("")
        else:
            # Python/TypeScript class page rendering
            if cls.init_params:
                lines.append("## Constructor\n")
                for p in cls.init_params:
                    default_str = f' default="{escape_for_table(p.default)}"' if p.default and p.default != "None" else ""
                    lines.extend([
                        f'<ParamField query="{p.name}" type="{escape_for_table(p.type, is_type=True)}" required={{"{true}" if p.required else "{false}"}}{default_str}>',
                        f'  {escape_mdx(p.description) if p.description else "No description available."}',
                        '</ParamField>',
                        ""
                    ])

            if cls.properties:
                lines.append("## Properties\n")
                for p in cls.properties:
                    lines.extend([
                        f'<ResponseField name="{p.name}" type="{escape_for_table(p.type, is_type=True)}">',
                        f'  {escape_mdx(p.description) if p.description else "No description available."}',
                        '</ResponseField>',
                        ""
                    ])

            if cls.methods or cls.class_methods:
                visible_class_methods = [m for m in cls.class_methods if m.name not in SKIP_METHODS]
                visible_methods = [m for m in cls.methods if m.name not in SKIP_METHODS]
                
                if visible_class_methods or visible_methods:
                    lines.append("## Methods\n")
                    lines.append("<CardGroup cols={2}>")
                    for m in visible_class_methods:
                        lines.append(f'  <Card title="{m.name}()" icon="function" href="../functions/{cls.name}-{m.name}">')
                        m_desc = sanitize_description(m.docstring) or "Class method."
                        lines.append(f"    {m_desc}")
                        lines.append("  </Card>")
                    for m in visible_methods:
                        lines.append(f'  <Card title="{m.name}()" icon="function" href="../functions/{cls.name}-{m.name}">')
                        m_desc = sanitize_description(m.docstring) or "Instance method."
                        lines.append(f"    {m_desc}")
                        lines.append("  </Card>")
                    lines.append("</CardGroup>\n")
                    
                # List skipped methods in an accordion without links for completeness
                skipped_methods = [m for m in (cls.class_methods + cls.methods) if m.name in SKIP_METHODS]
                if skipped_methods:
                    lines.append('<Accordion title="Internal & Generic Methods">')
                    for m in skipped_methods:
                        lines.append(f"- **{m.name}**: {sanitize_description(m.docstring) or 'Generic utility method.'}")
                    lines.append("</Accordion>\n")

        if cls.examples:
            lines.append("## Usage\n")
            if len(cls.examples) > 1:
                lines.append("<CodeGroup>")
                for i, ex in enumerate(cls.examples):
                    lines.append(f"```{lang} Example {i+1}\n{ex}\n```")
                lines.append("</CodeGroup>\n")
            else:
                lines.append(f"```{lang}\n{cls.examples[0]}\n```\n")

        return "\n".join(lines)

    def _render_function_page(self, func: FunctionInfo, module_info: ModuleInfo, cls_name: Optional[str] = None) -> str:
        """Render a dedicated Function/Method Source of Truth page."""
        safe_docstring = escape_mdx(func.docstring) if func.docstring else ""
        display_name = f"{cls_name}.{func.name}" if cls_name else func.name
        desc = sanitize_description(func.docstring) or f"API reference for {display_name}"
        title_suffix = self.config.get("title_suffix", "")
        
        lines = [
            "---",
            f'title: "{friendly_title(func.name, "function")}{title_suffix}"',
            f'sidebarTitle: "{friendly_title(func.name, "function")}"',
            f'description: "{func.name}: {desc}"',
            'icon: "function"',
            "---",
            "",
            f"# {func.name}",
            "",
            '<div className="flex items-center gap-2">',
        ]

        if func.is_async:
            lines.append('  <Badge color="blue">Async</Badge>')
        
        if cls_name:
            lines.append('  <Badge color="purple">Method</Badge>')
        else:
            lines.append('  <Badge color="teal">Function</Badge>')
            
        lines.append('</div>')
        lines.append("")

        if cls_name:
            lines.append(f"> This is a method of the [**{cls_name}**](../classes/{cls_name}) class in the [**{module_info.short_name}**](../modules/{module_info.short_name}) module.")
        else:
            lines.append(f"> This function is defined in the [**{module_info.short_name}**](../modules/{module_info.short_name}) module.")
            
        lines.extend([
            "",
            safe_docstring,
            "",
        ])

        # Add Mermaid Diagram if applicable
        mermaid = self._render_mermaid_diagram(func.name)
        if mermaid:
            lines.append(mermaid)
            lines.append("")

        lines.extend([
            "## Signature",
            "",
            "```python",
            f"{'async ' if func.is_async else ''}def {func.name}({func.signature}) -> {func.return_type}",
            "```",
            "",
        ])

        if func.params:
            lines.append("## Parameters\n")
            for i, p in enumerate(func.params):
                default_str = f' default="{escape_for_table(p.default)}"' if p.default and p.default != "None" else ""
                lines.extend([
                    f'<ParamField query="{p.name}" type="{escape_for_table(p.type, is_type=True)}" required={"{true}" if p.required else "{false}"}{default_str}>',
                    f'  {escape_mdx(p.description) if p.description else "No description available."}',
                    '</ParamField>',
                    ""
                ])

        if func.return_type and func.return_type != "None":
            ret_desc = func.return_description if func.return_description else "The result of the operation."
            lines.extend([
                "### Returns\n",
                f'<ResponseField name="Returns" type="{func.return_type}">',
                f"  {escape_mdx(ret_desc)}",
                "</ResponseField>",
                "",
            ])

        if func.raises:
            lines.append("### Exceptions\n")
            lines.append('<AccordionGroup>')
            for ex_type, ex_desc in func.raises:
                lines.append(f'  <Accordion title="{ex_type}">')
                lines.append(f'    {ex_desc}')
                lines.append('  </Accordion>')
            lines.append('</AccordionGroup>\n')

        if func.examples:
            lines.append("## Usage\n")
            if len(func.examples) > 1:
                lines.append("<CodeGroup>")
                for i, ex in enumerate(func.examples):
                    # Dedent example content for cleaner display
                    import textwrap
                    dedented_ex = textwrap.dedent(ex)
                    lines.append(f"```python Example {i+1}\n{dedented_ex}\n```")
                lines.append("</CodeGroup>\n")
            else:
                import textwrap
                dedented_ex = textwrap.dedent(func.examples[0])
                lines.append(f"```python\n{dedented_ex}\n```\n")

        return "\n".join(lines)

    def _render_mermaid_diagram(self, name: str) -> Optional[str]:
        """Auto-generate a Mermaid diagram based on function name and heuristics."""
        # Theme: Dark Red (#8B0000) for Agents/Inputs/Outputs, Teal (#189AB4) for Tools
        theme = """
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#8B0000', 'primaryTextColor': '#fff', 'primaryBorderColor': '#710101', 'lineColor': '#189AB4', 'secondaryColor': '#189AB4', 'tertiaryColor': '#fff' }}}%%
"""
        name_lower = name.lower()
        if "agent" in name_lower:
            return f"```mermaid{theme}\ngraph LR\n    input[\"Input Data\"] --> agent[\"Agent: {name}\"]\n    agent --> output[\"Output Result\"]\n    style agent fill:#8B0000,color:#fff\n    style input fill:#8B0000,color:#fff\n    style output fill:#8B0000,color:#fff\n```"
        if "tool" in name_lower:
            return f"```mermaid{theme}\ngraph LR\n    agent[\"Agent\"] -- \"uses\" --> tool[\"Tool: {name}\"]\n    tool -- \"returns\" --> result[\"Result\"]\n    style tool fill:#189AB4,color:#fff\n    style agent fill:#8B0000,color:#fff\n    style result fill:#8B0000,color:#fff\n```"
        if "hook" in name_lower:
            return f"```mermaid{theme}\ngraph TD\n    event[\"Event Trigger\"] --> hook[\"Hook: {name}\"]\n    hook --> decision{{\"Decision\"}}\n    decision -- \"Allow\" --> proc[\"Process\"]\n    decision -- \"Deny\" --> block[\"Block\"]\n    style hook fill:#189AB4,color:#fff\n    style event fill:#8B0000,color:#fff\n    style proc fill:#8B0000,color:#fff\n    style block fill:#8B0000,color:#fff\n```"
        return None

    def _render_class(self, cls: ClassInfo, package: str) -> List[str]:
        safe_docstring = escape_mdx(cls.docstring) if cls.docstring else ""
        lines = [f"### {cls.name}", ""]
        if cls.bases:
            lines.append(f"*Extends: {', '.join([sanitize_type_for_mdx(b) or b for b in cls.bases])}*")
            lines.append("")
        if safe_docstring:
            lines.append(safe_docstring)
            lines.append("")
        
        if cls.init_params:
            lines.extend([
                '<Accordion title="Constructor Parameters">',
                "",
                "| Parameter | Type | Required | Default |",
                "|-----------|------|----------|---------|",
            ])
            for p in cls.init_params:
                lines.append(f"| `{p.name}` | `{escape_for_table(p.type, is_type=True)}` | {'Yes' if p.required else 'No'} | `{escape_for_table(p.default, is_type=False) if p.default else '-'}` |")
            lines.append("</Accordion>\n")
        
        if cls.properties:
            lines.extend([
                '<Accordion title="Properties">',
                "",
                "| Property | Type |",
                "|----------|------|",
            ])
            for p in cls.properties:
                lines.append(f"| `{p.name}` | `{escape_for_table(p.type, is_type=True)}` |")
            lines.append("</Accordion>\n")
        
        if cls.methods:
            visible_methods = [m for m in cls.methods if m.name not in SKIP_METHODS]
            if visible_methods:
                lines.append('<Accordion title="Methods">')
                for m in visible_methods:
                    lines.append(f"- **{'async ' if m.is_async else ''}{m.name}**(`{escape_for_table(m.signature, is_type=True)}`) → `{escape_for_table(m.return_type, is_type=True)}`")
                    if m.docstring:
                        first_line = m.docstring.split('\n')[0][:80]
                        lines.append(f"  {escape_mdx(first_line)}")
                lines.append("</Accordion>\n")
        
        return lines

    def _render_function(self, func: FunctionInfo, package: str) -> List[str]:
        safe_docstring = escape_mdx(func.docstring) if func.docstring else ""
        async_prefix = "async " if func.is_async else ""
        
        lines = [f"### {func.name}()", ""]
        if safe_docstring:
            lines.append(safe_docstring)
            lines.append("")
        
        if package == "rust":
            lines.append(f"```rust\n{async_prefix}fn {func.name}({func.signature}) -> {func.return_type}\n```\n")
        elif package == "typescript":
            lines.append(f"```typescript\n{async_prefix}function {func.name}({func.signature}): {func.return_type}\n```\n")
        else:
            lines.append(f"```python\n{async_prefix}def {func.name}({func.signature}) -> {func.return_type}\n```\n")
        
        if func.params:
            lines.append('<Expandable title="Parameters">')
            for p in func.params:
                lines.append(f"- **{p.name}** (`{escape_for_table(p.type, is_type=True)}`)")
                if p.description: lines.append(f"  {escape_mdx(p.description)}")
            lines.append("</Expandable>\n")
        
        return lines


class ReferenceDocsGenerator:
    """Main generator class for PraisonAI reference documentation."""
    
    def __init__(
        self, 
        docs_root: str = "/Users/praison/PraisonAIDocs", 
        source_root: Optional[str] = None,
        layout: LayoutType = LayoutType.GRANULAR
    ):
        self.docs_root = Path(docs_root)
        self.docs_json_path = self.docs_root / "docs.json"
        self.layout = layout
        
        # Base source root - default to local development path if not provided
        base_src = Path(source_root) if source_root else Path("/Users/praison/praisonai-package")
        
        # Output sub-folders for Granular mode
        self.ref_base = self.docs_root / "docs/sdk/reference"
        
        self.paths = {
            "praisonaiagents": {
                "source": base_src / "src/praisonai-agents/praisonaiagents",
                "output": self.ref_base / "praisonaiagents",
                "import_prefix": "praisonaiagents",
                "badge_color": "blue",
                "badge_text": "AI Agent",
                "title_suffix": " • AI Agent SDK",
            },
            "praisonai": {
                "source": base_src / "src/praisonai/praisonai",
                "output": self.ref_base / "praisonai",
                "import_prefix": "praisonai",
                "badge_color": "purple",
                "badge_text": "AI Agent",
                "title_suffix": " • AI Agent SDK",
            },
            "typescript": {
                "source": base_src / "src/praisonai-ts/src",
                "output": self.ref_base / "typescript",
                "import_prefix": "praisonai",
                "badge_color": "green",
                "badge_text": "TypeScript AI Agent",
                "title_suffix": " • TypeScript AI Agent SDK",
            },
            "rust": {
                "source": base_src / "src/praisonai-rust",
                "output": self.ref_base / "rust",
                "import_prefix": "praisonai",
                "badge_color": "orange",
                "badge_text": "Rust AI Agent SDK",
                "title_suffix": " • Rust AI Agent SDK",
                "language": "rust",
            },
        }


    def generate_all(self, dry_run: bool = False):
        """Generate documentation for all packages."""
        for name in self.paths:
            self.generate_package(name, dry_run=dry_run)

    def generate_package(self, package_name: str, dry_run: bool = False):
        """Generate documentation for a specific package."""
        config = self.paths.get(package_name)
        if not config:
            print(f"Unknown package: {package_name}")
            return
        
        print(f"\n{'='*60}")
        print(f"Generating docs for: {package_name}")
        print(f"{'='*60}")
        
        if not config["source"].exists():
            print(f"Error: Source not found: {config['source']}")
            return
        
        if package_name == "typescript":
            parser = TypeScriptDocParser(config["source"])
        elif package_name == "rust":
            from .rust_parser import RustWorkspaceParser
            workspace_parser = RustWorkspaceParser(config["source"])
            # Parse all crates in the workspace
            all_modules = workspace_parser.parse_all()
            generator = MDXGenerator(config["output"], package_name, config, layout=self.layout)
            generated = 0
            for crate_name, modules in all_modules.items():
                print(f"  Crate: {crate_name} ({len(modules)} modules)")
                for info in modules:
                    if info.short_name in SKIP_MODULES:
                        continue
                    print(f"    Processing: {info.name}")
                    results = generator.generate_module_doc(info, dry_run=dry_run)
                    if results:
                        generated += 1
                        for r in results:
                            if dry_run:
                                print(f"      Would generate: {r.name}")
                            else:
                                print(f"      Generated: {r.name}")
            
            if generator.generated_files and not dry_run:
                print(f"\nCleaning up orphaned MDX files...")
                self.cleanup_orphaned_files(config["output"], generator.generated_files)
                print(f"\nUpdating docs.json navigation...")
                self.update_docs_json(package_name, sorted(list(generator.generated_files)))
            return
        else:
            parser = PythonDocParser(config["source"], config["import_prefix"])
        
        generator = MDXGenerator(config["output"], package_name, config, layout=self.layout)
        modules = parser.get_modules()
        print(f"Found {len(modules)} modules")
        
        generated = 0
        for module in modules:
            module_name = module.split(".")[-1] if "." in module else module
            if module_name in SKIP_MODULES:
                continue
            
            print(f"  Processing: {module}")
            info = parser.parse_module(module)
            if info:
                results = generator.generate_module_doc(info, dry_run=dry_run)
                if results:
                    generated += 1
                    for r in results:
                        if dry_run:
                            print(f"    Would generate: {r.name}")
                        else:
                            print(f"    Generated: {r.name}")
        
        if generator.generated_files and not dry_run:
            # NOTE: Cleanup disabled - was incorrectly deleting valid files
            # print(f"\nCleaning up orphaned MDX files...")
            # self.cleanup_orphaned_files(config["output"], generator.generated_files)
            
            print(f"\nUpdating docs.json navigation...")
            self.update_docs_json(package_name, sorted(list(generator.generated_files)))

    def cleanup_orphaned_files(self, output_dir: Path, current_files: set):
        """Delete MDX files that are no longer part of the generated set."""
        docs_root = Path("/Users/praison/PraisonAIDocs")
        for sub_dir in ["functions", "classes", "modules"]:
            target_dir = output_dir / sub_dir
            if not target_dir.exists():
                continue
                
            for mdx_file in target_dir.glob("*.mdx"):
                rel_path = str(mdx_file.relative_to(docs_root))
                nav_path = rel_path.replace('.mdx', '').replace('\\', '/')
                if nav_path not in current_files:
                    print(f"    Deleting orphaned file: {mdx_file.name}")
                    mdx_file.unlink()
            print(f"Updated package with {len(current_files)} pages")


    def update_docs_json(self, package_name: str, generated_pages: List[str]):
        """Update docs.json with generated reference pages."""
        if not self.docs_json_path.exists(): return
        
        try:
            with open(self.docs_json_path, 'r') as f:
                docs_config = json.load(f)
            
            sdk_tab = next((t for t in docs_config.get('navigation', {}).get('tabs', []) if t.get('tab') == 'SDK'), None)
            if not sdk_tab: return
            
            ref_group = next((g for g in sdk_tab.get('groups', []) if isinstance(g, dict) and g.get('group') == 'Reference'), None)
            if not ref_group: return
            
            package_group = next((pg for pg in ref_group.get('pages', []) if isinstance(pg, dict) and pg.get('group') == package_name), None)
            
            if not package_group:
                package_group = {"group": package_name, "pages": []}
                ref_group['pages'].append(package_group)
            
            unique_pages = sorted(list(set(generated_pages)))
            
            if self.layout == LayoutType.GRANULAR:
                modules = [p for p in unique_pages if '/modules/' in p]
                classes = [p for p in unique_pages if '/classes/' in p]
                functions = [p for p in unique_pages if '/functions/' in p]
                
                new_pages = []
                if modules:
                    new_pages.append({"group": "Modules", "icon": "box", "pages": modules})
                if classes:
                    new_pages.append({"group": "Classes", "icon": "brackets-curly", "pages": classes})
                if functions:
                    new_pages.append({"group": "Functions", "icon": "function", "pages": functions})
                
                package_group['pages'] = new_pages
            else:
                package_group['pages'] = [p for p in unique_pages if not p.lower().endswith(('/index', '/__init__'))]
            
            with open(self.docs_json_path, 'w') as f:
                json.dump(docs_config, f, indent=2)
                
        except Exception:
            pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PaisonAI Reference Documentation Generator")
    parser.add_argument("--layout", type=str, choices=["legacy", "granular"], default="granular", help="Documentation layout type")
    args = parser.parse_args()
    
    layout = LayoutType.LEGACY if args.layout == "legacy" else LayoutType.GRANULAR
    generator = ReferenceDocsGenerator(layout=layout)
    generator.generate_all()
