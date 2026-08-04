"""Compatibility shim for the reference docs generator.

The canonical implementation lives in
``praisonai_tools/docs_generator/generator.py``. This module re-exports the MDX
escaping / validation helpers so that test suites and tooling which import from
``scripts/generate_reference_docs.py`` resolve the same, single source of truth.

The generator module only depends on the Python standard library, so it is
loaded directly by file path. This avoids importing the top-level
``praisonai_tools`` package (which eagerly pulls in optional heavy
dependencies such as ``praisonaiagents``) and keeps this shim usable in a
lightweight docs/CI environment.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_GENERATOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "praisonai_tools"
    / "docs_generator"
    / "generator.py"
)

_spec = importlib.util.spec_from_file_location(
    "praisonai_tools_docs_generator", _GENERATOR_PATH
)
_generator = importlib.util.module_from_spec(_spec)
# Register before executing so dataclasses can resolve the module namespace.
import sys as _sys  # noqa: E402

_sys.modules[_spec.name] = _generator
_spec.loader.exec_module(_generator)

ICON_MAP = _generator.ICON_MAP
VALID_MDX_TAGS = _generator.VALID_MDX_TAGS
escape_for_table = _generator.escape_for_table
escape_mdx = _generator.escape_mdx
sanitize_description = _generator.sanitize_description
sanitize_type_for_mdx = _generator.sanitize_type_for_mdx
validate_docs_json_structure = _generator.validate_docs_json_structure
validate_mdx = _generator.validate_mdx

__all__ = [
    "ICON_MAP",
    "VALID_MDX_TAGS",
    "escape_for_table",
    "escape_mdx",
    "sanitize_description",
    "sanitize_type_for_mdx",
    "validate_docs_json_structure",
    "validate_mdx",
]
