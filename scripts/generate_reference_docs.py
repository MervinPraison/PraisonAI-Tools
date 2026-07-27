"""Compatibility shim for the reference documentation generator.

The canonical implementation lives in
``praisonai_tools/docs_generator/generator.py``. The test suites
(``tests/test_mdx_escaping.py`` and ``scripts/tests/test_mdx_escaping.py``)
add the ``scripts/`` directory to ``sys.path`` and import
``generate_reference_docs``, so this module re-exports the public API from the
canonical generator.

The generator is loaded directly from its file path so importing this shim does
not pull in the full ``praisonai_tools`` package (which has optional runtime
dependencies like ``praisonaiagents``).
"""

from __future__ import annotations

import importlib.util
import sys
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
if _spec is None or _spec.loader is None:  # pragma: no cover - defensive
    raise ImportError(f"Unable to load generator module from {_GENERATOR_PATH}")

_generator = importlib.util.module_from_spec(_spec)
# Register before executing so dataclasses defined in the module can resolve
# their own module namespace during class processing.
sys.modules[_spec.name] = _generator
_spec.loader.exec_module(_generator)

# Re-export the public MDX/documentation helpers used by the docs pipeline
# and the test suites.
sanitize_type_for_mdx = _generator.sanitize_type_for_mdx
escape_mdx = _generator.escape_mdx
escape_for_table = _generator.escape_for_table
validate_mdx = _generator.validate_mdx
validate_docs_json_structure = _generator.validate_docs_json_structure
sanitize_description = _generator.sanitize_description
VALID_MDX_TAGS = _generator.VALID_MDX_TAGS
ICON_MAP = _generator.ICON_MAP
get_icon_for_module = _generator.get_icon_for_module

__all__ = [
    "sanitize_type_for_mdx",
    "escape_mdx",
    "escape_for_table",
    "validate_mdx",
    "validate_docs_json_structure",
    "sanitize_description",
    "VALID_MDX_TAGS",
    "ICON_MAP",
    "get_icon_for_module",
]
