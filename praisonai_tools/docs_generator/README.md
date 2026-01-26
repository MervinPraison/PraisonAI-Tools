# PraisonAI Docs Generator

A powerful documentation generator for PraisonAI SDK reference documentation.

## Installation

```bash
pip install praisonai-tools
```

## Quick Start

### Using CLI

```bash
# Generate documentation with default settings
praisonai-tools docs-generate

# Generate with granular layout (separate pages for classes/functions)
praisonai-tools docs-generate --layout granular

# Specify custom output directory
praisonai-tools docs-generate --output /path/to/docs
```

### Using Python Module

```bash
# Run as module
python -m praisonai_tools.docs_generator

# With options
python -m praisonai_tools.docs_generator --layout granular
```

### Direct Script Execution

```bash
python generator.py --layout granular
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--layout` | Documentation layout: `compact` or `granular` | `granular` |
| `--output` | Output directory path | Auto-detected |

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

## Supported Packages

- `praisonaiagents` (Python Core SDK)
- `praisonai` (Python Wrapper)
- TypeScript SDK (`praisonai-ts`)

## Output Structure

```
docs/sdk/reference/
├── praisonaiagents/
│   ├── modules/      # Module hub pages
│   ├── classes/      # Class pages
│   └── functions/    # Function pages
├── praisonai/
│   └── ...
└── typescript/
    └── ...
```
