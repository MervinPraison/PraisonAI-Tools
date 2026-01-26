"""
Reference Documentation Generator for PraisonAI.

Generates Mintlify-compatible MDX documentation from Python and TypeScript source code.
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


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
    """Sanitize description for YAML frontmatter."""
    if not text:
        return ""
    
    first_line = text.split('\n')[0].strip()
    if len(first_line) > max_length:
        first_line = first_line[:max_length-3] + "..."
    
    first_line = first_line.replace('"', "'")
    first_line = re.sub(r'[<>{}]', '', first_line)
    
    return first_line


# =============================================================================
# CONFIGURATION
# =============================================================================

SKIP_MODULES = {
    "__pycache__", "_config", "_lazy", "_logging", "_warning_patch", 
    "_resolver_helpers", "audit", "lite", "profiling", "utils", "__init__",
    "_dev", "test", "tests", "__main__"
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
        except Exception:
            pass
    
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
    
    def __init__(self, output_dir: Path, package_name: str, config: dict):
        self.output_dir = output_dir
        self.package_name = package_name
        self.generated_files: List[str] = []
        self.config = config
    
    def generate_module_doc(self, info: ModuleInfo, dry_run: bool = False) -> Optional[Path]:
        """Generate MDX documentation for a module."""
        try:
            output_file = self.output_dir / f"{info.name}.mdx"
            content = self._render_module(info)
            
            if not dry_run:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(content)
                
                docs_root = Path("/Users/praison/PraisonAIDocs")
                rel_path = str(output_file.relative_to(docs_root))
                nav_path = rel_path.replace('.mdx', '').replace('\\', '/')
                self.generated_files.append(nav_path)
            
            return output_file
        except Exception:
            return None
    
    def _render_module(self, info: ModuleInfo) -> str:
        safe_docstring = escape_mdx(info.docstring) if info.docstring else ""
        desc = sanitize_description(info.docstring) or f"API reference for {info.name}"
        badge_color = self.config.get("badge_color", "gray")
        badge_text = self.config.get("badge_text", "Module")
        
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
            safe_docstring,
            "",
            "## Import",
            "",
            f"```{lang}",
            import_stmt,
            "```",
            "",
        ]
        
        if info.classes:
            lines.append("## Classes")
            lines.append("")
            for cls in info.classes:
                lines.extend(self._render_class(cls, info.package))
        
        if info.functions:
            lines.append("## Functions")
            lines.append("")
            for func in info.functions:
                lines.extend(self._render_function(func, info.package))
        
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
            lines.append('<Accordion title="Methods">')
            for m in cls.methods:
                lines.append(f"- **{'async ' if m.is_async else ''}{m.name}**(`{escape_for_table(m.signature, is_type=True)}`) → `{escape_for_table(m.return_type, is_type=True)}`")
                if m.docstring:
                    lines.append(f"  {escape_mdx(m.docstring.split('\\n')[0][:80])}")
            lines.append("</Accordion>\n")
        
        return lines

    def _render_function(self, func: FunctionInfo, package: str) -> List[str]:
        safe_docstring = escape_mdx(func.docstring) if func.docstring else ""
        async_prefix = "async " if func.is_async else ""
        lang = "typescript" if package == "typescript" else "python"
        
        lines = [f"### {func.name}()", ""]
        if safe_docstring:
            lines.append(safe_docstring)
            lines.append("")
        
        if lang == "python":
            lines.append(f"```python\n{async_prefix}def {func.name}({func.signature}) -> {func.return_type}\n```\n")
        else:
            lines.append(f"```typescript\n{async_prefix}function {func.name}({func.signature}): {func.return_type}\n```\n")
        
        if func.params:
            lines.append('<Expandable title="Parameters">')
            for p in func.params:
                lines.append(f"- **{p.name}** (`{escape_for_table(p.type, is_type=True)}`)")
                if p.description: lines.append(f"  {escape_mdx(p.description)}")
            lines.append("</Expandable>\n")
        
        return lines


class ReferenceDocsGenerator:
    """Main generator class for PraisonAI reference documentation."""
    
    def __init__(self, docs_root: str = "/Users/praison/PraisonAIDocs", source_root: Optional[str] = None):
        self.docs_root = Path(docs_root)
        self.docs_json_path = self.docs_root / "docs.json"
        
        # Base source root - default to local development path if not provided
        base_src = Path(source_root) if source_root else Path("/Users/praison/praisonai-package")
        
        self.paths = {
            "praisonaiagents": {
                "source": base_src / "src/praisonai-agents/praisonaiagents",
                "output": self.docs_root / "docs/sdk/reference/praisonaiagents",
                "import_prefix": "praisonaiagents",
                "badge_color": "blue",
                "badge_text": "Core SDK",
            },
            "praisonai": {
                "source": base_src / "src/praisonai/praisonai",
                "output": self.docs_root / "docs/sdk/reference/praisonai",
                "import_prefix": "praisonai",
                "badge_color": "purple",
                "badge_text": "Wrapper",
            },
            "typescript": {
                "source": base_src / "src/praisonai-ts/src",
                "output": self.docs_root / "docs/sdk/reference/typescript",
                "import_prefix": "praisonai",
                "badge_color": "green",
                "badge_text": "TypeScript",
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
        else:
            parser = PythonDocParser(config["source"], config["import_prefix"])
        
        generator = MDXGenerator(config["output"], package_name, config)
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
                result = generator.generate_module_doc(info, dry_run=dry_run)
                if result:
                    generated += 1
                    if dry_run:
                        print(f"    Would generate: {result.name}")
                    else:
                        print(f"    Generated: {result.name}")
        
        if generator.generated_files and not dry_run:
            print(f"\nUpdating docs.json navigation...")
            self.update_docs_json(package_name, generator.generated_files)
            print(f"Updated docs.json with {len(generator.generated_files)} pages")


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
            package_group['pages'] = [p for p in unique_pages if not p.lower().endswith(('/index', '/__init__'))]
            
            with open(self.docs_json_path, 'w') as f:
                json.dump(docs_config, f, indent=2)
                
        except Exception:
            pass
