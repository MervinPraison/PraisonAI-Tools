#!/usr/bin/env python3
"""
SDK Documentation Auto-Generator for PraisonAI.

Generates Mintlify-compatible MDX documentation from Python source code docstrings.

Usage:
    python generate-sdk-docs-v2.py --output /path/to/docs/sdk/reference/
    python generate-sdk-docs-v2.py --dry-run
    python generate-sdk-docs-v2.py --package praisonaiagents
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_PACKAGE_PATH = Path("/Users/praison/praisonai-package/src/praisonai-agents/praisonaiagents")
DEFAULT_OUTPUT_PATH = Path("/Users/praison/PraisonAIDocs/docs/sdk/reference/praisonaiagents")
DEFAULT_TEMPLATE_DIR = Path(__file__).parent / "templates"

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
}

SKIP_MODULES = ["__pycache__", "_config", "_lazy", "_logging", "_warning_patch", "_resolver_helpers", "audit", "lite", "profiling", "utils"]

DOCS_JSON_PATH = Path("/Users/praison/PraisonAIDocs/docs.json")
REFERENCE_NAV_GROUP = "API Reference (Auto-Generated)"


# =============================================================================
# MDX UTILITIES
# =============================================================================

def escape_mdx(text: str) -> str:
    """Escape text for MDX compatibility.
    
    MDX parses <word> as JSX components and {expr} as JSX expressions, so we need to:
    1. Wrap angle-bracketed words in backticks (inline code)
    2. Wrap curly-braced words in backticks (inline code)
    """
    if not text:
        return text
    
    # Pattern to match <word> or <word_with_underscores> not already in backticks
    # Negative lookbehind for backtick, match <identifier>, negative lookahead for backtick
    pattern = r'(?<!`)(<[a-zA-Z_][a-zA-Z0-9_]*>)(?!`)'
    text = re.sub(pattern, r'`\1`', text)
    
    # Pattern to match {word} placeholders not already in backticks
    # This handles things like {context}, {question}, {param_name}
    curly_pattern = r'(?<!`)(\{[a-zA-Z_][a-zA-Z0-9_]*\})(?!`)'
    text = re.sub(curly_pattern, r'`\1`', text)
    
    return text


def validate_mdx(content: str, filepath: str) -> List[str]:
    """Validate MDX content for common issues.
    
    Returns list of error messages (empty if valid).
    """
    errors = []
    lines = content.split('\n')
    in_code_block = False
    
    for i, line in enumerate(lines, 1):
        # Track code block state
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue
        
        # Skip lines inside code blocks
        if in_code_block:
            continue
        
        # Check for unescaped angle brackets (not in backticks)
        angle_matches = re.findall(r'(?<!`)(<[a-zA-Z_][a-zA-Z0-9_]*>)(?!`)', line)
        for match in angle_matches:
            errors.append(f"{filepath}:{i}: Unescaped JSX-like tag: {match}")
        
        # Check for unescaped curly braces (not in backticks)
        curly_matches = re.findall(r'(?<!`)(\{[a-zA-Z_][a-zA-Z0-9_]*\})(?!`)', line)
        for match in curly_matches:
            errors.append(f"{filepath}:{i}: Unescaped JSX expression: {match}")
    
    return errors


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ParamInfo:
    name: str
    type: str = "Any"
    default: Optional[str] = None
    description: str = ""
    required: bool = False


@dataclass
class MethodInfo:
    name: str
    signature: str = ""
    return_type: str = "None"
    docstring: str = ""
    params: List[ParamInfo] = field(default_factory=list)


@dataclass
class ClassInfo:
    name: str
    docstring: str = ""
    init_params: List[ParamInfo] = field(default_factory=list)
    methods: List[MethodInfo] = field(default_factory=list)


@dataclass
class FunctionInfo:
    name: str
    signature: str = ""
    return_type: str = "None"
    docstring: str = ""
    params: List[ParamInfo] = field(default_factory=list)


@dataclass
class ModuleInfo:
    name: str
    path: str
    docstring: str = ""
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    icon: str = "code"


# =============================================================================
# PARSER (AST-based)
# =============================================================================

class DocParser:
    """Parse Python source code using ast."""
    
    def __init__(self, package_path: Path):
        self.package_path = package_path
        self._lazy_imports: Dict[str, Tuple[str, str]] = {}
        self._load_lazy_imports()
    
    def _load_lazy_imports(self):
        """Load _LAZY_IMPORTS from __init__.py."""
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
    
    def get_public_symbols(self) -> Dict[str, Tuple[str, str]]:
        return self._lazy_imports.copy()
    
    def parse_module(self, module_path: str) -> Optional[ModuleInfo]:
        """Parse a module using ast."""
        try:
            rel_path = module_path.replace("praisonaiagents.", "").replace(".", "/")
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
            )
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                    class_info = self._parse_class(node)
                    if class_info:
                        info.classes.append(class_info)
                elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                    func_info = self._parse_function(node)
                    if func_info:
                        info.functions.append(func_info)
            
            return info
        except Exception as e:
            print(f"  Warning: Could not parse {module_path}: {e}")
            return None
    
    def _parse_class(self, node: ast.ClassDef) -> Optional[ClassInfo]:
        try:
            info = ClassInfo(name=node.name, docstring=ast.get_docstring(node) or "")
            
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    if item.name == "__init__":
                        for arg in item.args.args:
                            if arg.arg in ("self", "cls"):
                                continue
                            info.init_params.append(ParamInfo(
                                name=arg.arg,
                                type=self._get_annotation(arg.annotation),
                            ))
                    elif not item.name.startswith("_"):
                        method = self._parse_method(item)
                        if method:
                            info.methods.append(method)
            return info
        except Exception:
            return None
    
    def _parse_method(self, node: ast.FunctionDef) -> Optional[MethodInfo]:
        try:
            params = []
            sig_parts = []
            for arg in node.args.args:
                if arg.arg in ("self", "cls"):
                    continue
                param_type = self._get_annotation(arg.annotation)
                sig_parts.append(f"{arg.arg}: {param_type}")
                params.append(ParamInfo(name=arg.arg, type=param_type))
            
            return MethodInfo(
                name=node.name,
                signature=", ".join(sig_parts),
                return_type=self._get_annotation(node.returns),
                docstring=ast.get_docstring(node) or "",
                params=params,
            )
        except Exception:
            return None
    
    def _parse_function(self, node: ast.FunctionDef) -> Optional[FunctionInfo]:
        try:
            params = []
            sig_parts = []
            for arg in node.args.args:
                param_type = self._get_annotation(arg.annotation)
                sig_parts.append(f"{arg.arg}: {param_type}")
                params.append(ParamInfo(name=arg.arg, type=param_type))
            
            return FunctionInfo(
                name=node.name,
                signature=", ".join(sig_parts),
                return_type=self._get_annotation(node.returns),
                docstring=ast.get_docstring(node) or "",
                params=params,
            )
        except Exception:
            return None
    
    def _get_annotation(self, node) -> str:
        if node is None:
            return "Any"
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant):
            return str(node.value)
        try:
            return ast.unparse(node)
        except Exception:
            return "Any"


# =============================================================================
# GENERATOR
# =============================================================================

class DocGenerator:
    """Generate MDX documentation."""
    
    def __init__(self, template_dir: Path, output_dir: Path):
        self.template_dir = template_dir
        self.output_dir = output_dir
        self.generated_files: List[str] = []  # Track generated files for nav update
    
    def generate_module_doc(self, info: ModuleInfo, dry_run: bool = False) -> Optional[Path]:
        try:
            output_file = self.output_dir / f"{info.name}.mdx"
            content = self._render_module(info)
            
            # Validate MDX before writing
            errors = validate_mdx(content, str(output_file))
            if errors:
                for err in errors:
                    print(f"  MDX Warning: {err}")
            
            if dry_run:
                print(f"  Would generate: {output_file}")
                return None
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(content)
            
            # Track for nav update - use docs/ prefix for Mintlify
            # Path should be like: docs/sdk/reference/praisonaiagents/agent
            docs_root = output_file.parent.parent.parent.parent  # PraisonAIDocs
            rel_path = str(output_file.relative_to(docs_root))
            nav_path = rel_path.replace('.mdx', '').replace('\\', '/')
            self.generated_files.append(nav_path)
            
            return output_file
        except Exception as e:
            print(f"  Error generating {info.name}: {e}")
            return None
    
    def _render_module(self, info: ModuleInfo) -> str:
        # Escape docstring for MDX
        safe_docstring = escape_mdx(info.docstring) if info.docstring else ""
        # Truncate and escape description for frontmatter
        desc = info.docstring[:150].replace('"', "'") if info.docstring else f"API reference for {info.name}"
        desc = escape_mdx(desc)
        
        lines = [
            "---",
            f'title: "{info.name.title()} Module"',
            f'description: "{desc}"',
            f'icon: "{info.icon}"',
            "---",
            "",
            f"# {info.name}",
            "",
            safe_docstring,
            "",
            "## Import",
            "",
            "```python",
            f"from praisonaiagents import {info.name}",
            "```",
            "",
        ]
        
        if info.classes:
            lines.append("## Classes")
            lines.append("")
            for cls in info.classes:
                lines.extend(self._render_class(cls))
        
        if info.functions:
            lines.append("## Functions")
            lines.append("")
            for func in info.functions:
                lines.extend(self._render_function(func))
        
        return "\n".join(lines)
    
    def _render_class(self, cls: ClassInfo) -> List[str]:
        safe_docstring = escape_mdx(cls.docstring) if cls.docstring else ""
        lines = [
            f"### {cls.name}",
            "",
            safe_docstring,
            "",
        ]
        
        if cls.init_params:
            lines.append("#### Constructor Parameters")
            lines.append("")
            lines.append("| Parameter | Type | Description |")
            lines.append("|-----------|------|-------------|")
            for p in cls.init_params:
                lines.append(f"| `{p.name}` | `{p.type}` | {p.description} |")
            lines.append("")
        
        if cls.methods:
            lines.append("#### Methods")
            lines.append("")
            for m in cls.methods:
                lines.append(f"- **{m.name}**(`{m.signature}`) → `{m.return_type}`")
                if m.docstring:
                    safe_method_doc = escape_mdx(m.docstring[:100])
                    lines.append(f"  {safe_method_doc}")
            lines.append("")
        
        return lines
    
    def _render_function(self, func: FunctionInfo) -> List[str]:
        safe_docstring = escape_mdx(func.docstring) if func.docstring else ""
        return [
            f"### {func.name}()",
            "",
            safe_docstring,
            "",
            "```python",
            f"def {func.name}({func.signature}) -> {func.return_type}",
            "```",
            "",
        ]


# =============================================================================
# DOCS.JSON AUTO-UPDATE
# =============================================================================

def update_docs_json(generated_pages: List[str], dry_run: bool = False) -> bool:
    """Update docs.json with generated reference pages.
    
    This function:
    1. Reads the existing docs.json
    2. Finds or creates the "API Reference (Auto-Generated)" group
    3. Updates it with the new pages (avoiding duplicates)
    4. Writes back the updated JSON
    
    Returns True on success, False on failure.
    """
    import json
    
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
        
        # Find or create the auto-generated reference group
        ref_group = None
        for group in sdk_tab.get('groups', []):
            if isinstance(group, dict) and group.get('group') == REFERENCE_NAV_GROUP:
                ref_group = group
                break
        
        if not ref_group:
            # Create new group
            ref_group = {
                "group": REFERENCE_NAV_GROUP,
                "icon": "file-code",
                "pages": []
            }
            # Insert after the first group (SDK Reference)
            sdk_tab['groups'].insert(1, ref_group)
            print(f"  Created new navigation group: {REFERENCE_NAV_GROUP}")
        
        # Get existing pages to avoid duplicates
        existing_pages = set(ref_group.get('pages', []))
        new_pages = set(generated_pages)
        
        # Merge: keep existing, add new
        all_pages = sorted(existing_pages | new_pages)
        ref_group['pages'] = all_pages
        
        added_count = len(new_pages - existing_pages)
        
        if dry_run:
            print(f"  Would update docs.json: {added_count} new pages")
            return True
        
        # Write back
        with open(DOCS_JSON_PATH, 'w') as f:
            json.dump(docs_config, f, indent=2)
        
        print(f"  Updated docs.json: {len(all_pages)} pages ({added_count} new)")
        return True
        
    except Exception as e:
        print(f"  Error updating docs.json: {e}")
        return False


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate SDK documentation")
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--module", type=str, help="Generate for specific module only")
    parser.add_argument("--update-nav", action="store_true", help="Update docs.json navigation")
    args = parser.parse_args()
    
    start_time = time.time()
    
    print("=" * 60)
    print("PraisonAI SDK Documentation Generator")
    print("=" * 60)
    print(f"Package: {args.package}")
    print(f"Output: {args.output}")
    print(f"Dry run: {args.dry_run}")
    print()
    
    if not args.package.exists():
        print(f"Error: Package not found: {args.package}")
        return 1
    
    doc_parser = DocParser(args.package)
    generator = DocGenerator(DEFAULT_TEMPLATE_DIR, args.output)
    
    symbols = doc_parser.get_public_symbols()
    print(f"Found {len(symbols)} public symbols")
    
    # Group by module
    modules: Dict[str, List[str]] = {}
    for symbol, (module_path, _) in symbols.items():
        if module_path not in modules:
            modules[module_path] = []
        modules[module_path].append(symbol)
    
    print(f"Grouped into {len(modules)} modules")
    print()
    
    generated = 0
    errors = 0
    
    for module_path, symbol_list in sorted(modules.items()):
        if any(skip in module_path for skip in SKIP_MODULES):
            continue
        if args.module and args.module not in module_path:
            continue
        
        print(f"Processing: {module_path} ({len(symbol_list)} symbols)")
        
        info = doc_parser.parse_module(module_path)
        if not info:
            errors += 1
            continue
        
        result = generator.generate_module_doc(info, dry_run=args.dry_run)
        if result:
            generated += 1
            print(f"  Generated: {result.name}")
    
    # Update docs.json navigation if requested
    if args.update_nav and generator.generated_files:
        print()
        print("Updating docs.json navigation...")
        update_docs_json(generator.generated_files, dry_run=args.dry_run)
    
    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print(f"Generated: {generated} files")
    print(f"Errors: {errors}")
    print(f"Time: {elapsed:.2f}s")
    print("=" * 60)
    
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
