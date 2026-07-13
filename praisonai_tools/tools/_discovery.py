"""Automatic tool discovery for praisonai_tools.tools.

Builds a ``name -> module`` manifest by scanning the source of every tool
module in this package *without importing it*. Public top-level classes and
functions (names not starting with ``_``) become part of the public surface.

This preserves the per-symbol lazy import behaviour of the old hand-maintained
``tool_map`` while eliminating the three-place bookkeeping (the map plus two
``__all__`` blocks) that previously had to stay in lock-step. Adding a tool is
now just adding one module under ``praisonai_tools/tools/``.
"""

from __future__ import annotations

import ast
import logging
import os
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Modules in *this* package directory that are infrastructure, not tools.
# Their public symbols are exported explicitly by ``tools/__init__.py`` and
# must not be treated as discovered tools.
_SKIP_MODULES = {"__init__", "base", "decorator", "_discovery"}

# Tools that physically live outside ``praisonai_tools/tools/`` but have always
# been importable from it. Maps public symbol -> absolute module path.
_EXTERNAL_SYMBOLS: Dict[str, str] = {
    "N8nWorkflowTool": "praisonai_tools.n8n.n8n_workflow",
    "n8n_workflow": "praisonai_tools.n8n.n8n_workflow",
    "n8n_list_workflows": "praisonai_tools.n8n.n8n_workflow",
}


def _iter_public_symbols(source: str) -> List[str]:
    """Return public top-level class/function names defined in ``source``.

    Uses AST parsing so the module body is never executed (its heavy/optional
    dependencies are not imported at discovery time).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:  # pragma: no cover - defensive
        return []

    symbols: List[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                symbols.append(node.name)
    return symbols


def build_manifest(package_dir: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """Scan ``package_dir`` and build the discovery manifest.

    Returns a tuple ``(manifest, collisions)`` where ``manifest`` maps each
    public symbol name to the module it should be imported from, and
    ``collisions`` maps any symbol defined in more than one module to the list
    of modules that define it (first one wins in the manifest).
    """
    manifest: Dict[str, str] = {}
    collisions: Dict[str, List[str]] = {}

    for filename in sorted(os.listdir(package_dir)):
        if not filename.endswith(".py"):
            continue
        module_name = filename[:-3]
        if module_name in _SKIP_MODULES:
            continue

        path = os.path.join(package_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                source = fh.read()
        except OSError:  # pragma: no cover - defensive
            continue

        for symbol in _iter_public_symbols(source):
            if symbol in manifest and manifest[symbol] != module_name:
                collisions.setdefault(symbol, [manifest[symbol]])
                collisions[symbol].append(module_name)
                logger.warning(
                    "Tool discovery: symbol %r defined in both %r and %r; "
                    "keeping %r. Rename one to avoid shadowing.",
                    symbol, manifest[symbol], module_name, manifest[symbol],
                )
                continue
            manifest[symbol] = module_name

    # External tools that live in sibling packages but are re-exported here.
    for symbol, module in _EXTERNAL_SYMBOLS.items():
        manifest.setdefault(symbol, module)

    return manifest, collisions
