# PraisonAI Docs Generator

A powerful documentation generator for PraisonAI SDK reference documentation.

## Installation

```bash
pip install praisonai-tools
```

## Quick Start

### Generate Rust SDK Documentation (Standalone)

The Rust documentation generator works without dependencies:

```bash
# Direct execution (recommended for Rust)
cd praisonai_tools/docs_generator
python3 __main__.py --package rust

# Or use the standalone script
python3 generate_rust_docs.py --rust-path /path/to/praisonai-rust

# Dry run
python3 __main__.py --package rust --dry-run
```

### Generate All SDK Documentation

For Python/TypeScript docs, install the full package first:

```bash
pip install praisonaiagents
python -m praisonai_tools.docs_generator --package all
```

### Using CLI

```bash
# Generate documentation with default settings
praisonai-tools docs-generate

# Generate with granular layout (separate pages for classes/functions)
praisonai-tools docs-generate --layout granular

# Specify custom output directory
praisonai-tools docs-generate --output /path/to/docs
```

### Direct Script Execution

```bash
python generator.py --layout granular
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--layout` | Documentation layout: `compact` or `granular` | `granular` |
| `--package` | Package to generate: `praisonaiagents`, `praisonai`, `typescript`, `rust`, `all` | `all` |
| `--docs-root` | Root directory of the documentation repository | Auto-detected |
| `--dry-run` | Show what would be generated without writing files | `false` |

## Layouts

### Compact Layout
- Single page per module
- Classes and functions inline

### Granular Layout (Recommended)
- Separate pages for each class and function
- Module hub pages with links to components
- Better navigation and searchability

## Features

- **Dynamic lazy-loading support**: Captures `_LAZY_IMPORTS`, `_LAZY_GROUPS`, `TOOL_MAPPINGS`
- **Recursive scanning**: Scans all `__init__.py` files in package tree
- **MDX output**: Mintlify-compatible MDX format
- **Navigation generation**: Auto-updates `docs.json` navigation
- **Icon support**: Maps modules to Font Awesome icons
- **Multi-language support**: Python, TypeScript, and Rust

## Supported Packages

- `praisonaiagents` (Python Core SDK)
- `praisonai` (Python Wrapper)
- TypeScript SDK (`praisonai-ts`)
- **Rust SDK** (`praisonai-rust`) - Agent, Tools, Workflows, Memory, LLM

## Output Structure

```
docs/sdk/reference/
├── praisonaiagents/
│   ├── modules/      # Module hub pages
│   ├── classes/      # Class pages
│   └── functions/    # Function pages
├── praisonai/
│   └── ...
├── typescript/
│   └── ...
└── rust/
    ├── modules/      # praisonai.agent, praisonai.tools, etc.
    ├── classes/      # Agent, ToolRegistry, AgentTeam, etc.
    └── functions/    # Standalone functions
```
