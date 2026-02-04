#!/usr/bin/env python3
"""
Standalone Rust SDK documentation generator.
This can be run without the praisonaiagents dependency.
"""

import sys
import json
import argparse
from pathlib import Path

# Add docs_generator to path
sys.path.insert(0, str(Path(__file__).parent))

from rust_parser import RustWorkspaceParser


def escape_mdx(text: str) -> str:
    """Escape special MDX characters."""
    if not text:
        return ""
    return text.replace('<', '&lt;').replace('>', '&gt;').replace('{', '&#123;').replace('}', '&#125;')


def sanitize_description(text: str) -> str:
    """Sanitize description for frontmatter."""
    if not text:
        return ""
    return text.replace('"', "'").replace('\n', ' ')[:150]


# Icon map
ICON_MAP = {
    "agent": "robot", "tools": "wrench", "workflows": "route",
    "memory": "brain", "llm": "microchip", "config": "gear",
    "error": "circle-exclamation", "builder": "hammer",
    "derive": "wand-magic-sparkles", "cli": "terminal",
    "commands": "terminal", "default": "file-code"
}


def get_icon(name: str) -> str:
    """Get icon for module name."""
    return ICON_MAP.get(name.lower(), ICON_MAP["default"])


def generate_module_page(info, output_dir: Path, dry_run: bool = False) -> str:
    """Generate a module hub page."""
    short_name = info.short_name or info.name.split('.')[-1]
    desc = sanitize_description(info.docstring) or f"Rust module {short_name}"
    
    content = f'''---
title: "{short_name}"
description: "{desc}"
icon: "{get_icon(short_name)}"
---

# {info.name}

<Badge color="orange">Rust SDK</Badge>

{escape_mdx(info.docstring) if info.docstring else ""}

## Import

```rust
use {info.name.replace('.', '::')}::*;
```

'''
    
    if info.classes:
        content += "## Types\n\n<CardGroup cols={2}>\n"
        for cls in info.classes:
            cls_desc = sanitize_description(cls.docstring) or "Type definition."
            content += f'  <Card title="{cls.name}" icon="brackets-curly" href="../classes/{cls.name}">\n'
            content += f"    {cls_desc}\n"
            content += "  </Card>\n"
        content += "</CardGroup>\n\n"
    
    if info.functions:
        content += "## Functions\n\n<CardGroup cols={2}>\n"
        for func in info.functions:
            func_desc = sanitize_description(func.docstring) or "Function definition."
            content += f'  <Card title="{func.name}()" icon="function" href="../functions/{func.name}">\n'
            content += f"    {func_desc}\n"
            content += "  </Card>\n"
        content += "</CardGroup>\n\n"
    
    module_file = output_dir / 'modules' / f'{short_name}.mdx'
    if not dry_run:
        module_file.parent.mkdir(parents=True, exist_ok=True)
        module_file.write_text(content)
    
    return f"docs/sdk/reference/rust/modules/{short_name}"


def generate_class_page(cls, module_info, output_dir: Path, dry_run: bool = False) -> str:
    """Generate a class/struct page."""
    short_name = module_info.short_name or module_info.name.split('.')[-1]
    desc = sanitize_description(cls.docstring) or f"Class {cls.name}"
    
    content = f'''---
title: "{cls.name}"
description: "{desc}"
icon: "brackets-curly"
---

# {cls.name}

> Defined in the [**{short_name}**](../modules/{short_name}) module.

<Badge color="orange">Rust SDK</Badge>

{escape_mdx(cls.docstring) if cls.docstring else ""}

'''
    
    # Properties/Fields
    if cls.properties:
        content += "## Fields\n\n"
        content += "| Name | Type | Description |\n"
        content += "|------|------|-------------|\n"
        for p in cls.properties:
            p_type = escape_mdx(p.type) if hasattr(p, 'type') and p.type else "-"
            p_desc = escape_mdx(p.description)[:80] if hasattr(p, 'description') and p.description else "-"
            content += f"| `{p.name}` | `{p_type}` | {p_desc} |\n"
        content += "\n"
    
    # Methods
    if cls.methods:
        content += "## Methods\n\n"
        for m in cls.methods:
            async_prefix = "async " if hasattr(m, 'is_async') and m.is_async else ""
            ret_type = m.return_type if hasattr(m, 'return_type') and m.return_type else "()"
            content += f"### `{m.name}`\n\n"
            content += f"```rust\n{async_prefix}fn {m.name}({m.signature}) -> {ret_type}\n```\n\n"
            if hasattr(m, 'docstring') and m.docstring:
                content += f"{escape_mdx(m.docstring)}\n\n"
            if hasattr(m, 'params') and m.params:
                content += "**Parameters:**\n\n"
                content += "| Name | Type |\n|------|------|\n"
                for p in m.params:
                    p_type = escape_mdx(p.type) if hasattr(p, 'type') and p.type else "-"
                    content += f"| `{p.name}` | `{p_type}` |\n"
                content += "\n"
    
    class_file = output_dir / 'classes' / f'{cls.name}.mdx'
    if not dry_run:
        class_file.parent.mkdir(parents=True, exist_ok=True)
        class_file.write_text(content)
    
    return f"docs/sdk/reference/rust/classes/{cls.name}"


def generate_function_page(func, module_info, output_dir: Path, dry_run: bool = False) -> str:
    """Generate a function page."""
    short_name = module_info.short_name or module_info.name.split('.')[-1]
    desc = sanitize_description(func.docstring) or f"Function {func.name}"
    async_prefix = "async " if hasattr(func, 'is_async') and func.is_async else ""
    ret_type = func.return_type if hasattr(func, 'return_type') and func.return_type else "()"
    
    content = f'''---
title: "{func.name}"
description: "{desc}"
icon: "function"
---

# {func.name}()

> Defined in the [**{short_name}**](../modules/{short_name}) module.

<Badge color="orange">Rust SDK</Badge>

```rust
{async_prefix}fn {func.name}({func.signature}) -> {ret_type}
```

{escape_mdx(func.docstring) if func.docstring else ""}

'''
    
    if hasattr(func, 'params') and func.params:
        content += "## Parameters\n\n"
        content += "| Name | Type | Description |\n"
        content += "|------|------|-------------|\n"
        for p in func.params:
            p_type = escape_mdx(p.type) if hasattr(p, 'type') and p.type else "-"
            p_desc = escape_mdx(p.description) if hasattr(p, 'description') and p.description else "-"
            content += f"| `{p.name}` | `{p_type}` | {p_desc} |\n"
        content += "\n"
    
    func_file = output_dir / 'functions' / f'{func.name}.mdx'
    if not dry_run:
        func_file.parent.mkdir(parents=True, exist_ok=True)
        func_file.write_text(content)
    
    return f"docs/sdk/reference/rust/functions/{func.name}"


def update_docs_json(docs_json_path: Path, generated_files: list):
    """Update docs.json with Rust SDK navigation."""
    if not docs_json_path.exists():
        print(f"docs.json not found at {docs_json_path}")
        return
    
    with open(docs_json_path, 'r') as f:
        docs_config = json.load(f)
    
    # Find or create SDK tab
    sdk_tab = None
    for tab in docs_config.get('navigation', {}).get('tabs', []):
        if tab.get('tab') == 'SDK':
            sdk_tab = tab
            break
    
    if not sdk_tab:
        print("SDK tab not found in docs.json")
        return
    
    # Find Reference group
    ref_group = None
    for g in sdk_tab.get('groups', []):
        if isinstance(g, dict) and g.get('group') == 'Reference':
            ref_group = g
            break
    
    if not ref_group:
        print("Reference group not found in docs.json")
        return
    
    # Find or create rust group
    rust_group = None
    for pg in ref_group.get('pages', []):
        if isinstance(pg, dict) and pg.get('group') == 'rust':
            rust_group = pg
            break
    
    if not rust_group:
        rust_group = {"group": "rust", "pages": []}
        ref_group['pages'].append(rust_group)
    
    # Organize by type
    modules = sorted([p for p in generated_files if '/modules/' in p])
    classes = sorted([p for p in generated_files if '/classes/' in p])
    functions = sorted([p for p in generated_files if '/functions/' in p])
    
    new_pages = []
    if modules:
        new_pages.append({"group": "Modules", "icon": "box", "pages": modules})
    if classes:
        new_pages.append({"group": "Classes", "icon": "brackets-curly", "pages": classes})
    if functions:
        new_pages.append({"group": "Functions", "icon": "function", "pages": functions})
    
    rust_group['pages'] = new_pages
    
    with open(docs_json_path, 'w') as f:
        json.dump(docs_config, f, indent=2)
    
    print(f"Updated docs.json with Rust SDK navigation")


def main():
    parser = argparse.ArgumentParser(description="Generate Rust SDK documentation")
    parser.add_argument("--rust-path", default="/Users/praison/praisonai-package/src/praisonai-rust",
                        help="Path to Rust SDK workspace")
    parser.add_argument("--docs-root", default="/Users/praison/PraisonAIDocs",
                        help="Root directory of documentation")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files")
    args = parser.parse_args()
    
    rust_path = Path(args.rust_path)
    docs_root = Path(args.docs_root)
    output_dir = docs_root / 'docs/sdk/reference/rust'
    
    # Ensure directories exist
    if not args.dry_run:
        (output_dir / 'modules').mkdir(parents=True, exist_ok=True)
        (output_dir / 'classes').mkdir(parents=True, exist_ok=True)
        (output_dir / 'functions').mkdir(parents=True, exist_ok=True)
    
    # Parse all modules
    workspace_parser = RustWorkspaceParser(rust_path)
    all_modules = workspace_parser.parse_all()
    
    generated_files = []
    
    print("=" * 60)
    print("Generating Rust SDK Documentation")
    print("=" * 60)
    
    for crate_name, modules in all_modules.items():
        print(f"\nCrate: {crate_name}")
        
        for info in modules:
            # Skip empty modules
            if not info.classes and not info.functions:
                print(f"  Skipping empty: {info.name}")
                continue
            
            # Generate module page
            path = generate_module_page(info, output_dir, args.dry_run)
            generated_files.append(path)
            print(f"  Generated: modules/{info.short_name}.mdx")
            
            # Generate class pages
            for cls in info.classes:
                path = generate_class_page(cls, info, output_dir, args.dry_run)
                generated_files.append(path)
                print(f"    Class: classes/{cls.name}.mdx")
            
            # Generate function pages
            for func in info.functions:
                path = generate_function_page(func, info, output_dir, args.dry_run)
                generated_files.append(path)
                print(f"    Function: functions/{func.name}.mdx")
    
    print(f"\n=== Generated {len(generated_files)} files ===")
    
    # Update docs.json
    if not args.dry_run:
        update_docs_json(docs_root / 'docs.json', generated_files)


if __name__ == "__main__":
    main()
