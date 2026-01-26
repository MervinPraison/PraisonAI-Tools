#!/usr/bin/env python3
"""
Reference Documentation Generator for PraisonAI.

Generates Mintlify-compatible MDX documentation from Python and TypeScript source code.
Supports: praisonaiagents, praisonai, and praisonai-ts packages.

Features:
- Robust MDX escaping (curly braces, angle brackets, complex types)
- Automatic docs.json navigation updates with backup/rollback
- Beginner-friendly documentation with Mintlify components
- Mermaid diagrams with standard color scheme
- Dedicated icons for each module

Usage:
    python generate_reference_docs.py --package all
    python generate_reference_docs.py --package praisonaiagents
    python generate_reference_docs.py --package praisonai
    python generate_reference_docs.py --package typescript
    python generate_reference_docs.py --dry-run
    python generate_reference_docs.py --validate
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# =============================================================================
# CONFIGURATION
# =============================================================================

PATHS = {
    "praisonaiagents": {
        "source": Path("/Users/praison/praisonai-package/src/praisonai-agents/praisonaiagents"),
        "output": Path("/Users/praison/PraisonAIDocs/docs/sdk/reference/praisonaiagents"),
        "import_prefix": "praisonaiagents",
        "icon": "bot",
        "badge_color": "blue",
        "badge_text": "Core SDK",
    },
    "praisonai": {
        "source": Path("/Users/praison/praisonai-package/src/praisonai/praisonai"),
        "output": Path("/Users/praison/PraisonAIDocs/docs/sdk/reference/praisonai"),
        "import_prefix": "praisonai",
        "icon": "wand-sparkles",
        "badge_color": "purple",
        "badge_text": "Wrapper",
    },
    "typescript": {
        "source": Path("/Users/praison/praisonai-package/src/praisonai-ts/src"),
        "output": Path("/Users/praison/PraisonAIDocs/docs/sdk/reference/typescript"),
        "import_prefix": "praisonai",
        "icon": "file-code-2",
        "badge_color": "green",
        "badge_text": "TypeScript",
    },
}

DOCS_JSON_PATH = Path("/Users/praison/PraisonAIDocs/docs.json")

# Comprehensive icon mapping for all modules (Lucide icons)
ICON_MAP = {
    # Core agent modules
    "agent": "bot",
    "agents": "users",
    "autoagents": "sparkles",
    "auto_rag_agent": "search",
    
    # Task and workflow
    "task": "list-checks",
    "workflows": "git-branch",
    "process": "cog",
    
    # Tools
    "tools": "wrench",
    "tool": "wrench",
    
    # Memory and knowledge
    "memory": "brain",
    "knowledge": "book-open",
    "rag": "search",
    "embedding": "layers",
    "chunking": "scissors",
    
    # Session and state
    "session": "clock",
    "checkpoints": "save",
    "snapshot": "camera",
    "storage": "hard-drive",
    
    # Communication
    "mcp": "plug",
    "bus": "radio-tower",
    "handoff": "arrow-right-left",
    "streaming": "activity",
    
    # Safety and control
    "guardrails": "shield",
    "policy": "scale",
    "permissions": "lock",
    "approval": "circle-check",
    "escalation": "triangle-alert",
    
    # Planning and thinking
    "planning": "clipboard-list",
    "thinking": "lightbulb",
    
    # Hooks and plugins
    "hooks": "anchor",
    "plugins": "puzzle",
    
    # Observability
    "telemetry": "bar-chart-3",
    "trace": "activity",
    "eval": "flask-conical",
    
    # Context and config
    "context": "folder-open",
    "config": "settings",
    "fast": "zap",
    
    # UI and display
    "ui": "layout",
    "a2a": "message-square",
    "agui": "monitor",
    "flow_display": "git-graph",
    
    # Database
    "db": "database",
    
    # LLM
    "llm": "cpu",
    
    # Skills
    "skills": "graduation-cap",
    
    # Specialized agents
    "image_agent": "image",
    "video_agent": "video",
    "audio_agent": "mic",
    "ocr_agent": "scan",
    "deep_research_agent": "microscope",
    "query_rewriter_agent": "pencil",
    "prompt_expander_agent": "maximize",
    "context_agent": "file-text",
    "router_agent": "route",
    
    # Wrapper modules
    "cli": "terminal",
    "auto": "sparkles",
    "deploy": "rocket",
    "chainlit_ui": "message-circle",
    "profiler": "gauge",
    "scheduler": "calendar",
    "train": "dumbbell",
    "recipe": "chef-hat",
    "adapters": "plug-2",
    "integrations": "link",
    "jobs": "briefcase",
    "browser": "globe",
    "code": "code",
    "chat": "message-square",
    "endpoints": "server",
    "templates": "file-code",
    "setup": "settings-2",
    "replay": "repeat",
    "persistence": "save",
    "standardise": "align-left",
    "suite_runner": "play",
    "docs_runner": "book",
    "inbuilt_tools": "package",
    "mcp_server": "server",
    "capabilities": "star",
    "inc": "plus",
    "public": "globe",
    "version": "tag",
    "upload_vision": "upload",
    "train_vision": "eye",
    "agents_generator": "wand-2",
    "agent_scheduler": "calendar-clock",
    
    # TypeScript modules
    "ai": "brain-circuit",
    "cache": "database",
    "events": "bell",
    "observability": "eye",
    "db": "database",
    
    # Misc
    "main": "home",
    "server": "server",
    "lsp": "code-2",
    "obs": "eye",
    "output": "file-output",
    "compaction": "minimize-2",
    "background": "layers",
    "models": "box",
    "result": "check-square",
    "retrieval_config": "settings",
    "manager": "users-cog",
    "dimensions": "ruler",
    "embed": "layers",
    "feature_configs": "sliders",
    "param_resolver": "variable",
    "parse_utils": "file-search",
    "presets": "bookmark",
    
    # Default
    "default": "file-code",
    "index": "home",
    "types": "tag",
    "base": "database",
    "decorator": "sparkles",
    "utils": "wrench",
}




SKIP_MODULES = {
    "__pycache__", "_config", "_lazy", "_logging", "_warning_patch", 
    "_resolver_helpers", "audit", "lite", "profiling", "utils", "__init__",
    "_dev", "test", "tests", "__main__"
}

# Valid Mintlify/HTML tags that should NOT be escaped
VALID_MDX_TAGS = {
    # HTML tags
    'div', 'span', 'p', 'a', 'br', 'hr', 'img', 'ul', 'ol', 'li', 
    'table', 'tr', 'td', 'th', 'thead', 'tbody', 'code', 'pre',
    'strong', 'em', 'b', 'i', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    # Mintlify components
    'Card', 'CardGroup', 'Note', 'Warning', 'Info', 'Tip', 'Check',
    'Danger', 'Accordion', 'AccordionGroup', 'Tab', 'Tabs', 'Step',
    'Steps', 'Frame', 'Icon', 'Badge', 'Tooltip', 'CodeGroup',
    'Expandable', 'ParamField', 'ResponseField', 'Columns', 'Column',
    'RequestExample', 'ResponseExample', 'Banner', 'Update', 'View',
    'Tree', 'Tile', 'Tiles', 'Panel', 'Color'
}

# Mermaid color scheme
MERMAID_COLORS = {
    "agent": "#8B0000",  # Dark Red
    "tool": "#189AB4",   # Teal/Cyan
    "text": "#fff",      # White
}


# =============================================================================
# MDX SANITIZATION - ROBUST TYPE HANDLING
# =============================================================================

def sanitize_type_for_mdx(type_str: Optional[str]) -> Optional[str]:
    """Sanitize complex type annotations for MDX compatibility.
    
    Complex types like Callable[[X], Y] or Union[A, B] cause MDX parsing issues.
    This function simplifies them recursively.
    """
    if not type_str:
        return type_str
    
    result = type_str.strip()
    
    # Remove forward reference quotes
    result = re.sub(r"'([A-Z][a-zA-Z0-9_]*)'", r"\1", result)
    
    # Recursively simplify nested brackets
    while "[[" in result or " Union[" in result or " Optional[" in result:
        # Simplify [[X], Y] -> X, Y or similar
        new_result = re.sub(r"\[\[(.*?)\]\]", r"[\1]", result)
        if new_result == result:
            break
        result = new_result
        
    # If it's a complex type (has brackets), simplify to the base name
    if "[" in result:
        return result.split("[")[0]
        
    return result



def escape_mdx(text: str) -> str:
    """Escape text for MDX compatibility.
    
    MDX parses <word> as JSX components and {expr} as JSX expressions.
    This function protects code blocks and escapes literal text.
    """
    if not text:
        return text
        
    # Protect code blocks (fenced and inline)
    code_blocks = []
    def save_code_block(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks)-1}__"
    
    # Match fenced code blocks first, then inline code
    text = re.sub(r"```.*?```", save_code_block, text, flags=re.DOTALL)
    text = re.sub(r"`.*?`", save_code_block, text)
    
    # Escape ALL curly braces and angle brackets
    text = text.replace('{', '&#123;').replace('}', '&#125;')
    
    # Use HTML entities for angle brackets to be safe in all MDX contexts
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    
    # Restore code blocks
    for i, block in enumerate(code_blocks):
        text = text.replace(f"__CODE_BLOCK_{i}__", block)
        
    return text



def _escape_line(line: str, stripped: str) -> str:
    """Escape a single line for MDX compatibility."""
    # Skip if line is empty or only whitespace
    if not stripped:
        return line
    
    # Escape angle brackets: <word> -> `<word>`
    # But preserve valid Mintlify/HTML tags
    def escape_angle(match):
        full_match = match.group(0)
        tag = match.group(1)
        # Check if it's a valid tag (case-insensitive for HTML, case-sensitive for Mintlify)
        if tag in VALID_MDX_TAGS or tag.lower() in {t.lower() for t in VALID_MDX_TAGS if t.islower()}:
            return full_match
        return f'`{full_match}`'
    
    # Match <word> or <word_with_underscores> not already in backticks
    line = re.sub(r'(?<!`)(?<!\\)(<[a-zA-Z_][a-zA-Z0-9_]*>)(?!`)', escape_angle, line)
    
    # Escape curly braces: {word} -> `{word}`
    # Match {word} not already in backticks and not part of JSX attributes
    line = re.sub(r'(?<!`)(?<!\\)(?<!=)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!`)', r'`{\1}`', line)
    
    return line


def validate_mdx(content: str) -> List[str]:
    """Validate MDX content for common issues.
    
    Args:
        content: The MDX content to validate
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    lines = content.split('\n')
    in_code_block = False
    in_frontmatter = False
    frontmatter_count = 0
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Track frontmatter
        if stripped == '---':
            frontmatter_count += 1
            in_frontmatter = frontmatter_count == 1
            if frontmatter_count == 2:
                in_frontmatter = False
            continue
        
        if in_frontmatter:
            continue
        
        # Track code blocks
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            continue
        
        if in_code_block:
            continue
        
        # Check for unescaped angle brackets
        # Pattern: <word> not in backticks and not a valid tag
        angle_matches = re.findall(r'(?<!`)(<[a-zA-Z_][a-zA-Z0-9_]*>)(?!`)', line)
        for match in angle_matches:
            tag = match[1:-1]  # Remove < and >
            if tag not in VALID_MDX_TAGS and tag.lower() not in {t.lower() for t in VALID_MDX_TAGS if t.islower()}:
                errors.append(f"Line {i}: Unescaped JSX-like tag: {match}")
        
        # Check for unescaped curly braces
        curly_matches = re.findall(r'(?<!`)(?<!=)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!`)', line)
        for match in curly_matches:
            errors.append(f"Line {i}: Unescaped JSX expression: {{{match}}}")
    
    return errors


def escape_for_table(text: str) -> str:
    """Escape text for use in markdown tables.
    
    Args:
        text: The text to escape
        
    Returns:
        Table-safe text
    """
    if not text:
        return text
    
    # First sanitize complex types
    text = sanitize_type_for_mdx(text) or text
    
    # Escape pipe characters
    text = text.replace('|', '\\|')
    
    # Escape ALL curly braces - they cause MDX/JSX parsing issues
    text = text.replace('{', '\\{').replace('}', '\\}')
    
    # Escape angle brackets that could be parsed as JSX tags
    text = re.sub(r'<([a-zA-Z_][a-zA-Z0-9_]*)>', r'&lt;\1&gt;', text)
    
    return text


def sanitize_description(text: str, max_length: int = 150) -> str:
    """Sanitize description for YAML frontmatter.
    
    Args:
        text: The description text
        max_length: Maximum length
        
    Returns:
        Sanitized description
    """
    if not text:
        return ""
    
    # Take first line or first max_length chars
    first_line = text.split('\n')[0].strip()
    if len(first_line) > max_length:
        first_line = first_line[:max_length-3] + "..."
    
    # Escape quotes
    first_line = first_line.replace('"', "'")
    
    # Remove any MDX-problematic characters
    first_line = re.sub(r'[<>{}]', '', first_line)
    
    return first_line



def get_icon_for_module(module_name: str) -> str:
    """Get the icon name for a module.
    
    Args:
        module_name: Name of the module
        
    Returns:
        String icon name (Lucide/FontAwesome)
    """
    module_name = module_name.lower()
    
    # Try exact match first
    if module_name in ICON_MAP:
        return ICON_MAP[module_name]
    
    # Try partial match (keywords)
    if "agent" in module_name:
        return ICON_MAP["agent"]
    if "tool" in module_name:
        return ICON_MAP["tool"]
    if "task" in module_name:
        return ICON_MAP["task"]
    if "llm" in module_name:
        return ICON_MAP["llm"]
    if "config" in module_name:
        return ICON_MAP["config"]
    if "memory" in module_name:
        return ICON_MAP["memory"]
    if "knowledge" in module_name:
        return ICON_MAP["knowledge"]
    
    return ICON_MAP["default"]


def generate_mermaid_diagram(info: ModuleInfo) -> str:
    """Generate a Mermaid diagram for the module.
    
    Args:
        info: Module information
        
    Returns:
        Mermaid diagram code
    """
    # Color scheme: Dark Red (#8B0000) for agents/input/output, Teal (#189AB4) for tools
    agent_color = "fill:#8B0000,stroke:#8B0000,color:#fff"
    tool_color = "fill:#189AB4,stroke:#189AB4,color:#fff"
    
    lines = [
        "```mermaid",
        "graph TD",
    ]
    
    # Identify key components
    has_agent = any(c.name.lower() == "agent" or "agent" in c.name.lower() for c in info.classes)
    has_task = any(c.name.lower() == "task" for c in info.classes)
    has_tools = any("tool" in c.name.lower() or "skill" in c.name.lower() for c in info.classes + [ClassInfo(name=f.name) for f in info.functions])
    
    if has_agent:
        lines.append(f'    Agent["Agent"]:::agent')
        lines.append(f"    classDef agent {agent_color}")
        
        if has_tools:
            lines.append(f'    Tools["Tools"]:::tool')
            lines.append(f"    classDef tool {tool_color}")
            lines.append(f"    Agent --> Tools")
            
        if has_task:
            lines.append(f'    Task["Task"]:::agent')
            lines.append(f"    Task --> Agent")
    else:
        # Default generic diagram for other modules
        lines.append(f'    Module["{info.name}"]:::agent')
        lines.append(f"    classDef agent {agent_color}")
        if info.classes:
            for cls in info.classes[:3]: # limit to 3 classes
                lines.append(f'    {cls.name}["{cls.name}"]:::tool')
            lines.append(f"    classDef tool {tool_color}")
            for cls in info.classes[:3]:
                lines.append(f'    Module --> {cls.name}')
                
    lines.append("```")
    return "\n".join(lines)



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
    docstring: str = ""
    params: List[ParamInfo] = field(default_factory=list)
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


@dataclass
class FunctionInfo:
    name: str
    signature: str = ""
    return_type: str = "None"
    docstring: str = ""
    params: List[ParamInfo] = field(default_factory=list)
    is_async: bool = False


@dataclass
class ModuleInfo:
    name: str
    path: str
    docstring: str = ""
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    constants: List[Tuple[str, str]] = field(default_factory=list)
    icon: str = "file-code"
    package: str = "praisonaiagents"


# =============================================================================
# PYTHON PARSER (AST-based)
# =============================================================================

class PythonDocParser:
    """Parse Python source code using ast."""
    
    def __init__(self, package_path: Path, package_name: str):
        self.package_path = package_path
        self.package_name = package_name
        self._lazy_imports: Dict[str, Tuple[str, str]] = {}
        self._load_lazy_imports()
    
    def _load_lazy_imports(self):
        """Load _LAZY_IMPORTS from __init__.py if available."""
        init_file = self.package_path / "__init__.py"
        if not init_file.exists():
            return
        
        try:
            content = init_file.read_text()
            match = re.search(r'_LAZY_IMPORTS\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', content, re.DOTALL)
            if not match:
                return
            
            dict_content = match.group(1)
            pattern = r"'(\w+)':\s*\('([^']+)',\s*'([^']+)'\)"
            for m in re.finditer(pattern, dict_content):
                self._lazy_imports[m.group(1)] = (m.group(2), m.group(3))
        except Exception as e:
            print(f"  Warning: Could not load lazy imports: {e}")
    
    def get_modules(self) -> List[str]:
        """Get list of modules to document."""
        modules = set()
        
        # From lazy imports
        for symbol, (module_path, _) in self._lazy_imports.items():
            modules.add(module_path)
        
        # From directory structure
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
            
            module_name = module_path.split(".")[-1]
            info = ModuleInfo(
                name=module_name,
                path=module_path,
                docstring=ast.get_docstring(tree) or "",
                icon=get_icon_for_module(module_name),
                package=self.package_name,
            )
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                    class_info = self._parse_class(node)
                    if class_info:
                        info.classes.append(class_info)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                    func_info = self._parse_function(node)
                    if func_info:
                        info.functions.append(func_info)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            info.constants.append((target.id, self._get_value(node.value)))
            
            return info
        except Exception as e:
            print(f"  Warning: Could not parse {module_path}: {e}")
            return None
    
    def _parse_class(self, node: ast.ClassDef) -> Optional[ClassInfo]:
        try:
            bases = [self._get_annotation(b) for b in node.bases]
            info = ClassInfo(
                name=node.name, 
                docstring=ast.get_docstring(node) or "",
                bases=bases,
            )
            
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name == "__init__":
                        info.init_params = self._parse_params(item)
                    elif not item.name.startswith("_"):
                        method = self._parse_method(item)
                        if method:
                            if method.is_classmethod:
                                info.class_methods.append(method)
                            else:
                                info.methods.append(method)
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
            
            params = self._parse_params(node)
            sig_parts = [f"{p.name}: {p.type}" for p in params]
            
            return MethodInfo(
                name=node.name,
                signature=", ".join(sig_parts),
                return_type=self._get_annotation(node.returns),
                docstring=ast.get_docstring(node) or "",
                params=params,
                is_async=is_async,
                is_static=is_static,
                is_classmethod=is_classmethod,
            )
        except Exception:
            return None
    
    def _parse_function(self, node) -> Optional[FunctionInfo]:
        try:
            is_async = isinstance(node, ast.AsyncFunctionDef)
            params = self._parse_params(node)
            sig_parts = [f"{p.name}: {p.type}" for p in params]
            
            return FunctionInfo(
                name=node.name,
                signature=", ".join(sig_parts),
                return_type=self._get_annotation(node.returns),
                docstring=ast.get_docstring(node) or "",
                params=params,
                is_async=is_async,
            )
        except Exception:
            return None
    
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
        if node is None:
            return "Any"
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant):
            return repr(node.value)
        try:
            return ast.unparse(node)
        except Exception:
            return "Any"
    
    def _get_value(self, node) -> str:
        if node is None:
            return "None"
        if isinstance(node, ast.Constant):
            return repr(node.value)
        try:
            return ast.unparse(node)
        except Exception:
            return "..."


# =============================================================================
# TYPESCRIPT PARSER
# =============================================================================

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
            
            info = ModuleInfo(
                name=module_name,
                path=f"praisonai/{module_name}",
                docstring=self._extract_module_doc(content),
                icon=get_icon_for_module(module_name),
                package="typescript",
            )
            
            info.classes = self._parse_classes(content)
            info.functions = self._parse_functions(content)
            
            return info
        except Exception as e:
            print(f"  Warning: Could not parse {module_name}: {e}")
            return None
    
    def _extract_module_doc(self, content: str) -> str:
        """Extract module-level JSDoc comment."""
        match = re.search(r'^/\*\*\s*(.*?)\s*\*/', content, re.DOTALL)
        if match:
            doc = match.group(1)
            doc = re.sub(r'\n\s*\*\s*', '\n', doc)
            doc = re.sub(r'@\w+.*', '', doc)
            return doc.strip()
        return ""
    
    def _parse_classes(self, content: str) -> List[ClassInfo]:
        """Parse class exports from TypeScript."""
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
        """Parse function exports from TypeScript."""
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
# MDX GENERATOR
# =============================================================================

class MDXGenerator:
    """Generate MDX documentation files."""
    
    def __init__(self, output_dir: Path, package_name: str):
        self.output_dir = output_dir
        self.package_name = package_name
        self.generated_files: List[str] = []
        self.config = PATHS.get(package_name, {})
    
    def generate_module_doc(self, info: ModuleInfo, dry_run: bool = False) -> Optional[Path]:
        """Generate MDX documentation for a module."""
        try:
            output_file = self.output_dir / f"{info.name}.mdx"
            content = self._render_module(info)
            
            # Validate MDX before writing
            errors = validate_mdx(content)
            if errors:
                print(f"  MDX validation warnings in {info.name}:")
                for err in errors[:5]:  # Show first 5 errors
                    print(f"    - {err}")
                if len(errors) > 5:
                    print(f"    ... and {len(errors) - 5} more")
            
            if dry_run:
                print(f"  Would generate: {output_file}")
                return None
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(content)
            
            # Track for nav update
            docs_root = Path("/Users/praison/PraisonAIDocs")
            rel_path = str(output_file.relative_to(docs_root))
            nav_path = rel_path.replace('.mdx', '').replace('\\', '/')
            self.generated_files.append(nav_path)
            
            return output_file
        except Exception as e:
            print(f"  Error generating {info.name}: {e}")
            return None
    
    def _render_module(self, info: ModuleInfo) -> str:
        """Render module documentation as MDX."""
        safe_docstring = escape_mdx(info.docstring) if info.docstring else ""
        desc = sanitize_description(info.docstring) or f"API reference for {info.name}"
        
        # Get badge configuration
        badge_color = self.config.get("badge_color", "gray")
        badge_text = self.config.get("badge_text", "Module")
        
        # Determine import statement based on package
        if info.package == "typescript":
            import_stmt = f"import {{ {info.name} }} from 'praisonai';"
            lang = "typescript"
        else:
            import_stmt = f"from {info.package} import {info.name}"
            lang = "python"
        
        lines = [
            "---",
            f'title: "{info.name}"',
            f'description: "{desc}"',
            f'icon: "{info.icon}"',
            "---",
            "",
            f"# {info.name}",
            "",
            f'<Badge color="{badge_color}">{badge_text}</Badge>',
            "",
        ]
        

        
        if safe_docstring:
            lines.append(safe_docstring)
            lines.append("")
        
        # Import section
        lines.extend([
            "## Import",
            "",
            f"```{lang}",
            import_stmt,
            "```",
            "",
        ])
        
        # Classes section
        if info.classes:
            lines.append("## Classes")
            lines.append("")
            for cls in info.classes:
                lines.extend(self._render_class(cls, info.package))
        
        # Functions section
        if info.functions:
            lines.append("## Functions")
            lines.append("")
            for func in info.functions:
                lines.extend(self._render_function(func, info.package))
        
        # Constants section
        if info.constants:
            lines.append("## Constants")
            lines.append("")
            lines.append("| Name | Value |")
            lines.append("|------|-------|")
            for name, value in info.constants:
                safe_value = escape_for_table(str(value)[:50])
                lines.append(f"| `{name}` | `{safe_value}` |")
            lines.append("")
        
        return "\n".join(lines)

    
    def _render_class(self, cls: ClassInfo, package: str) -> List[str]:
        """Render class documentation."""
        safe_docstring = escape_mdx(cls.docstring) if cls.docstring else ""
        
        lines = [
            f"### {cls.name}",
            "",
        ]
        
        if cls.bases:
            safe_bases = [sanitize_type_for_mdx(b) or b for b in cls.bases]
            lines.append(f"*Extends: {', '.join(safe_bases)}*")
            lines.append("")
        
        if safe_docstring:
            lines.append(safe_docstring)
            lines.append("")
        
        # Constructor parameters
        if cls.init_params:
            lines.append('<Accordion title="Constructor Parameters">')
            lines.append("")
            lines.append("| Parameter | Type | Required | Default |")
            lines.append("|-----------|------|----------|---------|")
            for p in cls.init_params:
                safe_type = escape_for_table(p.type)
                default = escape_for_table(p.default) if p.default else "-"
                required = "Yes" if p.required else "No"
                lines.append(f"| `{p.name}` | `{safe_type}` | {required} | `{default}` |")
            lines.append("")
            lines.append("</Accordion>")
            lines.append("")
        
        # Properties
        if cls.properties:
            lines.append('<Accordion title="Properties">')
            lines.append("")
            lines.append("| Property | Type |")
            lines.append("|----------|------|")
            for p in cls.properties:
                safe_type = escape_for_table(p.type)
                lines.append(f"| `{p.name}` | `{safe_type}` |")
            lines.append("")
            lines.append("</Accordion>")
            lines.append("")
        
        # Methods
        if cls.methods:
            lines.append('<Accordion title="Methods">')
            lines.append("")
            for m in cls.methods:
                async_prefix = "async " if m.is_async else ""
                safe_sig = escape_for_table(m.signature)
                safe_ret = escape_for_table(m.return_type)
                lines.append(f"- **{async_prefix}{m.name}**(`{safe_sig}`) → `{safe_ret}`")
                if m.docstring:
                    first_line = m.docstring.split('\n')[0][:80]
                    safe_doc = escape_mdx(first_line)
                    lines.append(f"  {safe_doc}")
            lines.append("")
            lines.append("</Accordion>")
            lines.append("")
        
        return lines

    
    def _render_function(self, func: FunctionInfo, package: str) -> List[str]:
        """Render function documentation."""
        safe_docstring = escape_mdx(func.docstring) if func.docstring else ""
        async_prefix = "async " if func.is_async else ""
        lang = "typescript" if package == "typescript" else "python"
        
        lines = [
            f"### {func.name}()",
            "",
        ]
        
        if safe_docstring:
            lines.append(safe_docstring)
            lines.append("")
        
        # Signature
        safe_sig = sanitize_type_for_mdx(func.signature) or func.signature
        safe_ret = sanitize_type_for_mdx(func.return_type) or func.return_type
        
        if lang == "python":
            lines.extend([
                "```python",
                f"{async_prefix}def {func.name}({safe_sig}) -> {safe_ret}",
                "```",
                "",
            ])
        else:
            lines.extend([
                "```typescript",
                f"{async_prefix}function {func.name}({safe_sig}): {safe_ret}",
                "```",
                "",
            ])
        
        # Parameters
        if func.params:
            lines.append('<Expandable title="Parameters">')
            lines.append("")
            for p in func.params:
                safe_type = escape_for_table(p.type)
                lines.append(f"- **{p.name}** (`{safe_type}`)")
                if p.description:
                    lines.append(f"  {escape_mdx(p.description)}")
            lines.append("")
            lines.append("</Expandable>")
            lines.append("")
        
        return lines



# =============================================================================
# DOCS.JSON UPDATER
# =============================================================================

def validate_docs_json_structure(docs_config: dict) -> List[str]:
    """Validate docs.json has required structure.
    
    Args:
        docs_config: The parsed docs.json content
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Check navigation exists
    if "navigation" not in docs_config:
        errors.append("Missing 'navigation' key")
        return errors
    
    nav = docs_config["navigation"]
    
    # Check tabs exist
    if "tabs" not in nav:
        errors.append("Missing 'navigation.tabs' key")
        return errors
    
    # Check SDK tab exists
    sdk_tab = None
    for tab in nav.get("tabs", []):
        if tab.get("tab") == "SDK":
            sdk_tab = tab
            break
    
    if not sdk_tab:
        errors.append("Missing 'SDK' tab in navigation")
        return errors
    
    # Check Reference group exists
    ref_group = None
    for group in sdk_tab.get("groups", []):
        if isinstance(group, dict) and group.get("group") == "Reference":
            ref_group = group
            break
    
    if not ref_group:
        errors.append("Missing 'Reference' group in SDK tab")
    
    return errors


def update_docs_json(package_name: str, generated_pages: List[str], dry_run: bool = False) -> bool:
    """Update docs.json with generated reference pages.
    
    Args:
        package_name: The package name (praisonaiagents, praisonai, typescript)
        generated_pages: List of generated page paths
        dry_run: If True, don't write changes
        
    Returns:
        True on success, False on failure
    """
    if not DOCS_JSON_PATH.exists():
        print(f"  Warning: docs.json not found at {DOCS_JSON_PATH}")
        return False
    
    backup_path = DOCS_JSON_PATH.with_suffix('.json.bak')
    
    try:
        # Create backup
        if not dry_run:
            shutil.copy(DOCS_JSON_PATH, backup_path)
            print(f"  Created backup: {backup_path}")
        
        with open(DOCS_JSON_PATH, 'r') as f:
            docs_config = json.load(f)
        
        # Validate structure
        errors = validate_docs_json_structure(docs_config)
        if errors:
            print(f"  docs.json structure errors:")
            for err in errors:
                print(f"    - {err}")
            return False
        
        # Find the SDK tab
        sdk_tab = None
        for tab in docs_config.get('navigation', {}).get('tabs', []):
            if tab.get('tab') == 'SDK':
                sdk_tab = tab
                break
        
        # Find the Reference group
        ref_group = None
        for group in sdk_tab.get('groups', []):
            if isinstance(group, dict) and group.get('group') == 'Reference':
                ref_group = group
                break
        
        # Find or create the package subgroup
        package_group = None
        for pg in ref_group.get('pages', []):
            if isinstance(pg, dict) and pg.get('group') == package_name:
                package_group = pg
                break
        
        if not package_group:
            # Create new package group
            package_config = PATHS.get(package_name, {})
            package_group = {
                "group": package_name,
                "icon": package_config.get("icon", "file-code"),
                "pages": []
            }
            ref_group['pages'].append(package_group)
        
        # Update pages
        new_page_objects = []
        # Deduplicate and filter out common index/utility modules that shouldn't be in main reference
        unique_pages = sorted(list(set(generated_pages)))
        for page_path in unique_pages:
            module_name = page_path.split('/')[-1]
            if module_name.lower() == "index" or module_name.lower() == "__init__":
                continue
                
            # Use string paths to rely on MDX frontmatter icons and fix redirection issues
            new_page_objects.append(page_path)

        
        # Merge with existing if necessary, or just overwrite for reference docs
        # Since these are auto-generated reference docs, overwriting is safer to keep it clean
        package_group['pages'] = new_page_objects
        
        added_count = len(generated_pages)


        
        if dry_run:
            print(f"  Would update docs.json: {added_count} new pages for {package_name}")
            return True
        
        # Write back
        with open(DOCS_JSON_PATH, 'w') as f:
            json.dump(docs_config, f, indent=2)
        
        print(f"  Updated docs.json: {len(new_page_objects)} pages for {package_name} ({added_count} new)")

        return True
        
    except Exception as e:
        print(f"  Error updating docs.json: {e}")
        # Attempt rollback
        if backup_path.exists() and not dry_run:
            try:
                shutil.copy(backup_path, DOCS_JSON_PATH)
                print(f"  Rolled back to backup")
            except Exception as rollback_error:
                print(f"  Rollback failed: {rollback_error}")
        return False


# =============================================================================
# MAIN
# =============================================================================

def generate_package_docs(package_name: str, dry_run: bool = False) -> Tuple[int, int]:
    """Generate documentation for a package.
    
    Args:
        package_name: The package to generate docs for
        dry_run: If True, don't write files
        
    Returns:
        Tuple of (generated_count, error_count)
    """
    config = PATHS.get(package_name)
    if not config:
        print(f"Unknown package: {package_name}")
        return 0, 1
    
    print(f"\n{'='*60}")
    print(f"Generating docs for: {package_name}")
    print(f"{'='*60}")
    print(f"Source: {config['source']}")
    print(f"Output: {config['output']}")
    
    if not config['source'].exists():
        print(f"Error: Source not found: {config['source']}")
        return 0, 1
    
    # Create parser based on package type
    if package_name == "typescript":
        parser = TypeScriptDocParser(config['source'])
    else:
        parser = PythonDocParser(config['source'], config['import_prefix'])
    
    generator = MDXGenerator(config['output'], package_name)
    
    modules = parser.get_modules()
    print(f"Found {len(modules)} modules")
    
    generated = 0
    errors = 0
    
    for module in modules:
        module_name = module.split(".")[-1] if "." in module else module
        if module_name in SKIP_MODULES:
            continue
        
        print(f"  Processing: {module}")
        
        info = parser.parse_module(module)
        if not info:
            errors += 1
            continue
        
        result = generator.generate_module_doc(info, dry_run=dry_run)
        if result:
            generated += 1
            print(f"    Generated: {result.name}")
    
    # Update docs.json
    if generator.generated_files and not dry_run:
        print(f"\nUpdating docs.json navigation...")
        update_docs_json(package_name, generator.generated_files, dry_run=dry_run)
    
    return generated, errors


def main():
    parser = argparse.ArgumentParser(description="Generate Reference Documentation")
    parser.add_argument("--package", choices=["praisonaiagents", "praisonai", "typescript", "all"], 
                        default="all", help="Package to generate docs for")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files")
    parser.add_argument("--validate", action="store_true", help="Validate existing docs only")
    args = parser.parse_args()
    
    start_time = time.time()
    
    print("=" * 60)
    print("PraisonAI Reference Documentation Generator")
    print("=" * 60)
    
    if args.validate:
        print("Validation mode - checking existing docs...")
        # TODO: Implement validation of existing docs
        return 0
    
    total_generated = 0
    total_errors = 0
    
    packages = ["praisonaiagents", "praisonai", "typescript"] if args.package == "all" else [args.package]
    
    for pkg in packages:
        generated, errors = generate_package_docs(pkg, dry_run=args.dry_run)
        total_generated += generated
        total_errors += errors
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print(f"Total Generated: {total_generated} files")
    print(f"Total Errors: {total_errors}")
    print(f"Time: {elapsed:.2f}s")
    print("=" * 60)
    
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
