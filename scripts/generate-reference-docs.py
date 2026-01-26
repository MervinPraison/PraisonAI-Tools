#!/usr/bin/env python3
"""
Reference Documentation Generator for PraisonAI.

Generates Mintlify-compatible MDX documentation from Python and TypeScript source code.
Supports: praisonaiagents, praisonai, and praisonai-ts packages.

Features:
- Robust MDX escaping (curly braces, angle brackets)
- Automatic docs.json navigation updates
- Beginner-friendly documentation with Mintlify components
- Mermaid diagrams with standard color scheme

Usage:
    python generate-reference-docs.py --all
    python generate-reference-docs.py --package praisonaiagents
    python generate-reference-docs.py --package praisonai
    python generate-reference-docs.py --package typescript
"""

from __future__ import annotations

import argparse
import ast
import json
import re
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
        "icon": "robot",
    },
    "praisonai": {
        "source": Path("/Users/praison/praisonai-package/src/praisonai/praisonai"),
        "output": Path("/Users/praison/PraisonAIDocs/docs/sdk/reference/praisonai"),
        "import_prefix": "praisonai",
        "icon": "wand-magic-sparkles",
    },
    "typescript": {
        "source": Path("/Users/praison/praisonai-package/src/praisonai-ts/src"),
        "output": Path("/Users/praison/PraisonAIDocs/docs/sdk/reference/typescript"),
        "import_prefix": "praisonai",
        "icon": "js",
    },
}

DOCS_JSON_PATH = Path("/Users/praison/PraisonAIDocs/docs.json")

ICON_MAP = {
    "agent": "robot",
    "agents": "users",
    "task": "list-check",
    "tools": "wrench",
    "memory": "brain",
    "knowledge": "book",
    "workflows": "sitemap",
    "hooks": "link",
    "trace": "chart-line",
    "bus": "tower-broadcast",
    "plugins": "puzzle-piece",
    "config": "gear",
    "guardrails": "shield",
    "planning": "clipboard-list",
    "session": "clock",
    "mcp": "plug",
    "eval": "flask",
    "rag": "magnifying-glass",
    "context": "folder-open",
    "ui": "window-maximize",
    "db": "database",
    "embedding": "vector-square",
    "skills": "graduation-cap",
    "handoff": "arrow-right-arrow-left",
    "telemetry": "chart-line",
    "policy": "gavel",
    "auto": "wand-magic-sparkles",
    "deploy": "rocket",
    "cli": "terminal",
    "llm": "microchip",
    "cache": "database",
    "process": "gears",
}

SKIP_MODULES = {
    "__pycache__", "_config", "_lazy", "_logging", "_warning_patch", 
    "_resolver_helpers", "audit", "lite", "profiling", "utils", "__init__",
    "_dev", "test", "tests", "__main__"
}

# Mermaid color scheme
MERMAID_COLORS = {
    "agent": "#8B0000",  # Dark Red
    "tool": "#189AB4",   # Teal/Cyan
    "text": "#fff",      # White
}


# =============================================================================
# MDX UTILITIES - ROBUST ESCAPING
# =============================================================================

def escape_mdx(text: str) -> str:
    """Escape text for MDX compatibility.
    
    MDX parses <word> as JSX components and {expr} as JSX expressions.
    We need to wrap these in backticks to prevent parsing errors.
    
    Also handles docstrings with code examples by wrapping them in code blocks.
    """
    if not text:
        return text
    
    # Check if text looks like it contains code examples (indented lines with code patterns)
    lines = text.split('\n')
    result_lines = []
    in_code_block = False
    in_docstring_code = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Track explicit code blocks
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            result_lines.append(line)
            continue
        
        if in_code_block:
            result_lines.append(line)
            continue
        
        # Detect docstring code examples (indented lines starting with common code patterns)
        if (line.startswith('    ') and 
            (stripped.startswith('from ') or stripped.startswith('import ') or 
             stripped.startswith('agent') or stripped.startswith('app') or
             stripped.startswith('#') or stripped.startswith('GET ') or 
             stripped.startswith('POST ') or '=' in stripped[:20])):
            if not in_docstring_code:
                # Start a code block
                result_lines.append('```python')
                in_docstring_code = True
            result_lines.append(stripped)
            continue
        elif in_docstring_code and (not line.startswith('    ') or stripped == ''):
            # End the code block
            result_lines.append('```')
            in_docstring_code = False
            if stripped:
                result_lines.append(line)
            continue
        
        # Escape angle brackets and curly braces outside code blocks
        # Valid Mintlify/HTML tags that should not be escaped
        valid_tags = {'div', 'span', 'p', 'a', 'br', 'hr', 'img', 'ul', 'ol', 'li', 
                      'table', 'tr', 'td', 'th', 'thead', 'tbody', 'code', 'pre',
                      'strong', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                      'Card', 'CardGroup', 'Note', 'Warning', 'Info', 'Tip', 'Check',
                      'Danger', 'Accordion', 'AccordionGroup', 'Tab', 'Tabs', 'Step',
                      'Steps', 'Frame', 'Icon', 'Badge', 'Tooltip', 'CodeGroup',
                      'Expandable', 'ParamField', 'ResponseField'}
        
        def escape_angle(match):
            tag = match.group(1)
            if tag.lower() in {t.lower() for t in valid_tags}:
                return match.group(0)
            return f'`<{tag}>`'
        
        line = re.sub(r'(?<!`)(?<!\\)<([a-zA-Z_][a-zA-Z0-9_]*)>(?!`)', escape_angle, line)
        line = re.sub(r'(?<!`)(?<!\\)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!`)', r'`{\1}`', line)
        
        result_lines.append(line)
    
    # Close any unclosed code block
    if in_docstring_code:
        result_lines.append('```')
    
    return '\n'.join(result_lines)


def simplify_type(text: str) -> str:
    """Simplify complex type annotations for MDX compatibility.
    
    Complex types like Callable[[X], Y] or Union[A, B] cause MDX parsing issues.
    We simplify them to be more readable and MDX-safe.
    """
    if not text:
        return text
    
    # Replace complex Callable types with simpler representation
    text = re.sub(r"Callable\[\[[^\]]*\],\s*[^\]]+\]", "Callable", text)
    text = re.sub(r"Callable\[\.\.\.,\s*[^\]]+\]", "Callable", text)
    
    # Simplify nested Optional/Union/List types
    # Optional[List[Union[...]]] -> Optional[List]
    text = re.sub(r"Optional\[List\[Union\[[^\]]+\]\]\]", "Optional[List]", text)
    text = re.sub(r"Optional\[Union\[[^\]]+\]\]", "Optional", text)
    text = re.sub(r"Union\[[^\]]+\]", "Union", text)
    
    # Remove forward references (quoted type names)
    text = re.sub(r"'([A-Z][a-zA-Z0-9_]*)'", r"\1", text)
    
    # Simplify Dict types
    text = re.sub(r"Dict\[str,\s*[^\]]+\]", "Dict", text)
    text = re.sub(r"Dict\[[^\]]+\]", "Dict", text)
    
    # Simplify List types  
    text = re.sub(r"List\[[^\]]+\]", "List", text)
    
    # Simplify Tuple types
    text = re.sub(r"Tuple\[[^\]]+\]", "Tuple", text)
    
    # Simplify Coroutine types
    text = re.sub(r"Coroutine\[[^\]]+\]", "Coroutine", text)
    
    return text


def escape_for_table(text: str) -> str:
    """Escape text for use in markdown tables."""
    if not text:
        return text
    
    # First simplify complex types
    text = simplify_type(text)
    
    # Escape pipe characters
    text = text.replace('|', '\\|')
    
    return text


def sanitize_description(text: str, max_length: int = 150) -> str:
    """Sanitize description for frontmatter."""
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
    icon: str = "code"
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
        
        content = init_file.read_text()
        match = re.search(r'_LAZY_IMPORTS\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', content, re.DOTALL)
        if not match:
            return
        
        dict_content = match.group(1)
        pattern = r"'(\w+)':\s*\('([^']+)',\s*'([^']+)'\)"
        for m in re.finditer(pattern, dict_content):
            self._lazy_imports[m.group(1)] = (m.group(2), m.group(3))
    
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
                icon=ICON_MAP.get(module_name, "code"),
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
            # Try single file
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
                icon=ICON_MAP.get(module_name, "code"),
                package="typescript",
            )
            
            # Parse exports
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
            # Clean up JSDoc formatting
            doc = re.sub(r'\n\s*\*\s*', '\n', doc)
            doc = re.sub(r'@\w+.*', '', doc)
            return doc.strip()
        return ""
    
    def _parse_classes(self, content: str) -> List[ClassInfo]:
        """Parse class exports from TypeScript."""
        classes = []
        
        # Match class declarations
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
        
        # Match function exports
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
    
    def generate_module_doc(self, info: ModuleInfo, dry_run: bool = False) -> Optional[Path]:
        """Generate MDX documentation for a module."""
        try:
            output_file = self.output_dir / f"{info.name}.mdx"
            content = self._render_module(info)
            
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
        ]
        
        # Add badge for package
        if info.package == "praisonaiagents":
            lines.append('<Badge>Core SDK</Badge>')
        elif info.package == "praisonai":
            lines.append('<Badge variant="info">Wrapper</Badge>')
        else:
            lines.append('<Badge variant="success">TypeScript</Badge>')
        lines.append("")
        
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
            lines.append(f"*Extends: {', '.join(cls.bases)}*")
            lines.append("")
        
        if safe_docstring:
            lines.append(safe_docstring)
            lines.append("")
        
        # Constructor parameters
        if cls.init_params:
            lines.append("<Accordion title=\"Constructor Parameters\">")
            lines.append("")
            lines.append("| Parameter | Type | Required | Default |")
            lines.append("|-----------|------|----------|---------|")
            for p in cls.init_params:
                safe_type = escape_for_table(p.type)
                default = escape_for_table(p.default) if p.default else "-"
                required = "✓" if p.required else ""
                lines.append(f"| `{p.name}` | `{safe_type}` | {required} | {default} |")
            lines.append("")
            lines.append("</Accordion>")
            lines.append("")
        
        # Properties
        if cls.properties:
            lines.append("<Accordion title=\"Properties\">")
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
            lines.append("<Accordion title=\"Methods\">")
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
        safe_sig = escape_mdx(func.signature)
        safe_ret = escape_mdx(func.return_type)
        
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
            lines.append("<Expandable title=\"Parameters\">")
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

def update_docs_json(package_name: str, generated_pages: List[str], dry_run: bool = False) -> bool:
    """Update docs.json with generated reference pages."""
    if not DOCS_JSON_PATH.exists():
        print(f"  Warning: docs.json not found at {DOCS_JSON_PATH}")
        return False
    
    try:
        with open(DOCS_JSON_PATH, 'r') as f:
            docs_config = json.load(f)
        
        # Find the SDK tab
        sdk_tab = None
        for tab in docs_config.get('navigation', {}).get('tabs', []):
            if tab.get('tab') == 'SDK':
                sdk_tab = tab
                break
        
        if not sdk_tab:
            print("  Warning: SDK tab not found in docs.json")
            return False
        
        # Find the Reference group
        ref_group = None
        for group in sdk_tab.get('groups', []):
            if isinstance(group, dict) and group.get('group') == 'Reference':
                ref_group = group
                break
        
        if not ref_group:
            print("  Warning: Reference group not found in docs.json")
            return False
        
        # Find or create the package subgroup
        package_group = None
        for pg in ref_group.get('pages', []):
            if isinstance(pg, dict) and pg.get('group') == package_name:
                package_group = pg
                break
        
        if not package_group:
            # Create new package group
            package_group = {
                "group": package_name,
                "icon": PATHS[package_name]["icon"],
                "pages": []
            }
            ref_group['pages'].append(package_group)
        
        # Update pages
        existing_pages = set(package_group.get('pages', []))
        new_pages = set(generated_pages)
        all_pages = sorted(existing_pages | new_pages)
        package_group['pages'] = all_pages
        
        added_count = len(new_pages - existing_pages)
        
        if dry_run:
            print(f"  Would update docs.json: {added_count} new pages for {package_name}")
            return True
        
        # Write back
        with open(DOCS_JSON_PATH, 'w') as f:
            json.dump(docs_config, f, indent=2)
        
        print(f"  Updated docs.json: {len(all_pages)} pages for {package_name} ({added_count} new)")
        return True
        
    except Exception as e:
        print(f"  Error updating docs.json: {e}")
        return False


# =============================================================================
# MAIN
# =============================================================================

def generate_package_docs(package_name: str, dry_run: bool = False) -> Tuple[int, int]:
    """Generate documentation for a package."""
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
    args = parser.parse_args()
    
    start_time = time.time()
    
    print("=" * 60)
    print("PraisonAI Reference Documentation Generator")
    print("=" * 60)
    
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
