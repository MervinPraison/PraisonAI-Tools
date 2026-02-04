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


def sanitize_description(text: str, max_len: int = 150) -> str:
    """Sanitize description for frontmatter. Truncates at word boundary."""
    if not text:
        return ""
    clean = text.replace('"', "'").replace('\n', ' ').strip()
    if len(clean) <= max_len:
        return clean
    # Truncate at word boundary
    truncated = clean[:max_len].rsplit(' ', 1)[0]
    return truncated + "..."


# Icon map
ICON_MAP = {
    "agent": "robot", "tools": "wrench", "workflows": "route",
    "memory": "brain", "llm": "microchip", "config": "gear",
    "error": "circle-exclamation", "builder": "hammer",
    "derive": "wand-magic-sparkles", "cli": "terminal",
    "commands": "terminal", "default": "file-code"
}

# Friendly title mappings for modules
MODULE_TITLES = {
    "agent": "Agent",
    "builder": "Agent Builder",
    "config": "Configuration",
    "error": "Error Handling",
    "llm": "LLM Providers",
    "memory": "Memory",
    "tools": "Tools",
    "workflows": "Workflows",
    "praisonai_derive": "Derive Macros",
    "chat": "Chat Command",
    "prompt": "Prompt Command",
    "run": "Run Command",
}

# Rich descriptions for modules (used when docstring is empty or as fallback)
MODULE_DESCRIPTIONS = {
    "agent": "Core AI Agent implementation for building intelligent agents in Rust",
    "builder": "Fluent builder pattern for constructing Rust AI agents",
    "config": "Configuration types for PraisonAI Rust AI agents",
    "error": "Error handling utilities for Rust AI agent operations",
    "llm": "LLM provider abstractions for Rust AI agents (OpenAI, Anthropic, Ollama)",
    "memory": "Memory and conversation history for Rust AI agents",
    "tools": "Tool system for extending Rust AI agent capabilities",
    "workflows": "Multi-agent workflow patterns for Rust AI orchestration",
    "praisonai_derive": "Procedural macros for defining Rust AI agent tools",
    "chat": "Interactive chat command for Rust AI agents",
    "prompt": "Single-shot prompt execution for Rust AI agents",
    "run": "Workflow execution command for Rust AI agents",
}

# Abbreviations to preserve in titles
ABBREVIATIONS = {"llm", "api", "cli", "id", "url", "http", "ai", "io"}


def friendly_title(name: str, page_type: str = "class") -> str:
    """Convert a name to a friendly, human-readable title.
    
    Args:
        name: The raw name (e.g., "AgentBuilder", "praisonai_derive")
        page_type: One of "module", "class", "function"
    """
    # Check for explicit module title mapping
    if page_type == "module" and name.lower() in MODULE_TITLES:
        return MODULE_TITLES[name.lower()]
    
    # For functions, add parentheses
    if page_type == "function":
        # Special case for macros
        if name == "tool":
            return "#[tool] Macro"
        return f"{name}()"
    
    # Convert snake_case to Title Case
    if "_" in name:
        parts = name.split("_")
        titled_parts = []
        for part in parts:
            if part.lower() in ABBREVIATIONS:
                titled_parts.append(part.upper())
            else:
                titled_parts.append(part.capitalize())
        return " ".join(titled_parts)
    
    # Convert PascalCase to Title Case with spaces
    # e.g., "AgentBuilder" -> "Agent Builder", "LlmConfig" -> "LLM Config"
    result = []
    current_word = []
    
    for i, char in enumerate(name):
        if char.isupper():
            # Check if this is part of an abbreviation
            if current_word:
                word = "".join(current_word)
                # If previous chars form an abbreviation, keep them together
                if word.lower() in ABBREVIATIONS:
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
        if word.lower() in ABBREVIATIONS:
            result.append(word.upper())
        else:
            result.append(word)
    
    # Join and fix common patterns
    title = " ".join(result)
    
    # Fix cases like "L L M" -> "LLM"
    for abbr in ABBREVIATIONS:
        spaced = " ".join(abbr.upper())
        if spaced in title:
            title = title.replace(spaced, abbr.upper())
    
    return title


def get_icon(name: str) -> str:
    """Get icon for module name."""
    return ICON_MAP.get(name.lower(), ICON_MAP["default"])


def generate_module_page(info, output_dir: Path, dry_run: bool = False) -> str:
    """Generate a module hub page."""
    short_name = info.short_name or info.name.split('.')[-1]
    title = friendly_title(short_name, "module")
    title_suffix = " • Rust AI Agent SDK"
    # Use docstring if available, otherwise use our rich descriptions
    desc = sanitize_description(info.docstring) or MODULE_DESCRIPTIONS.get(short_name.lower(), f"Rust AI Agent SDK - {title}")
    
    content = f'''---
title: "{title}{title_suffix}"
sidebarTitle: "{title}"
description: "{desc}"
icon: "{get_icon(short_name)}"
---

# {short_name}

<Badge color="orange">Rust AI Agent SDK</Badge>

{escape_mdx(info.docstring) if info.docstring else ""}

## Import

```rust
use {info.name.replace('.', '::')}::*;
```

'''
    
    if info.classes:
        content += "## Types\n\n<CardGroup cols={2}>\n"
        for cls in info.classes:
            cls_title = friendly_title(cls.name, "class")
            cls_desc = sanitize_description(cls.docstring) or "Type definition."
            content += f'  <Card title="{cls_title}" icon="brackets-curly" href="../classes/{cls.name}">\n'
            content += f"    {cls_desc}\n"
            content += "  </Card>\n"
        content += "</CardGroup>\n\n"
    
    if info.functions:
        content += "## Functions\n\n<CardGroup cols={2}>\n"
        for func in info.functions:
            func_title = friendly_title(func.name, "function")
            func_desc = sanitize_description(func.docstring) or "Function definition."
            content += f'  <Card title="{func_title}" icon="function" href="../functions/{func.name}">\n'
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
    module_title = friendly_title(short_name, "module")
    title = friendly_title(cls.name, "class")
    title_suffix = " • Rust AI Agent SDK"
    # Include original name in description for searchability
    base_desc = sanitize_description(cls.docstring) if cls.docstring else f"{cls.name} struct for Rust AI agents"
    desc = f"{base_desc}" if cls.name in base_desc else f"{cls.name}: {base_desc}"
    
    content = f'''---
title: "{title}{title_suffix}"
sidebarTitle: "{title}"
description: "{desc}"
icon: "brackets-curly"
---

# {cls.name}

> Defined in the [**{module_title}**](../modules/{short_name}) module.

<Badge color="orange">Rust AI Agent SDK</Badge>

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
    module_title = friendly_title(short_name, "module")
    title = friendly_title(func.name, "function")
    title_suffix = " • Rust AI Agent SDK"
    # Include original name in description for searchability
    base_desc = sanitize_description(func.docstring) if func.docstring else f"{func.name} function for Rust AI agents"
    desc = f"{base_desc}" if func.name in base_desc else f"{func.name}: {base_desc}"
    async_prefix = "async " if hasattr(func, 'is_async') and func.is_async else ""
    ret_type = func.return_type if hasattr(func, 'return_type') and func.return_type else "()"
    
    content = f'''---
title: "{title}{title_suffix}"
sidebarTitle: "{title}"
description: "{desc}"
icon: "function"
---

# {func.name}

> Defined in the [**{module_title}**](../modules/{short_name}) module.

<Badge color="orange">Rust AI Agent SDK</Badge>

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
