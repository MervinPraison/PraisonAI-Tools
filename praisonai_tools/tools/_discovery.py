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
import json
import logging
import os
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Cache file name written alongside the tools package. Bumping ``_CACHE_VERSION``
# invalidates all previously written caches after a discovery-format change.
_CACHE_VERSION = 1
_CACHE_FILENAME = f"._discovery_cache_v{_CACHE_VERSION}.json"

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


def _extract_all(tree: ast.Module) -> List[str] | None:
    """Return the names listed in a module-level ``__all__``, if declared.

    Only literal string entries are honoured. Returns ``None`` when the module
    does not declare ``__all__`` at the top level.
    """
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                    names: List[str] = []
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            names.append(elt.value)
                    return names
    return None


def _iter_public_symbols(source: str, module_name: str = "<unknown>") -> List[str]:
    """Return the public top-level symbol names exported by ``source``.

    Uses AST parsing so the module body is never executed (its heavy/optional
    dependencies are not imported at discovery time).

    Resolution order:
    1. If the module declares ``__all__``, honour it verbatim (author intent).
       This lets a module opt its module-level re-export aliases into the public
       surface (e.g. ``read_yaml = _yaml_tools.read_yaml``) or, conversely,
       narrow what is exported.
    2. Otherwise, collect public top-level classes and functions. Bare
       assignment aliases are intentionally *not* auto-exported without an
       explicit ``__all__``: several ``*_tools.py`` modules bind the same
       helper names (``read_csv``/``read_excel``/…) that would otherwise
       collide across modules and were never part of the historical public API.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:  # pragma: no cover - defensive
        logger.warning(
            "Tool discovery: could not parse %r (%s); its tools will not be "
            "discoverable. Fix the syntax error to restore them.",
            module_name, exc,
        )
        return []

    explicit = _extract_all(tree)
    if explicit is not None:
        return [name for name in explicit if not name.startswith("_")]

    symbols: List[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                symbols.append(node.name)
    return symbols


def _fingerprint(package_dir: str) -> str:
    """Cheap directory fingerprint used to validate the discovery cache.

    Reflects the set of ``.py`` files and their size/mtime, so any edit,
    addition, or removal of a tool module invalidates the cache (keeping
    discovery fully automatic) without re-parsing on every import.
    """
    parts: List[str] = [f"v{_CACHE_VERSION}"]
    for filename in sorted(os.listdir(package_dir)):
        if not filename.endswith(".py"):
            continue
        try:
            st = os.stat(os.path.join(package_dir, filename))
        except OSError:  # pragma: no cover - defensive
            continue
        parts.append(f"{filename}:{st.st_size}:{st.st_mtime_ns}")
    return "|".join(parts)


def build_manifest(package_dir: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """Return the discovery manifest for ``package_dir``, using a disk cache.

    The manifest is expensive to compute (it AST-parses every tool module), so
    the result is memoised in a small JSON file next to the package and reused
    while the directory fingerprint is unchanged. The cache is best-effort:
    any read/write/validation failure falls back to a live scan, so behaviour
    is always correct even on read-only installs.
    """
    cache_path = os.path.join(package_dir, _CACHE_FILENAME)
    fingerprint = _fingerprint(package_dir)

    try:
        with open(cache_path, "r", encoding="utf-8") as fh:
            cached = json.load(fh)
        if cached.get("fingerprint") == fingerprint:
            return cached["manifest"], cached["collisions"]
    except (OSError, ValueError, KeyError):
        pass  # No/invalid cache -> scan below.

    manifest, collisions = _scan_manifest(package_dir)

    try:
        tmp_path = f"{cache_path}.{os.getpid()}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "fingerprint": fingerprint,
                    "manifest": manifest,
                    "collisions": collisions,
                },
                fh,
            )
        os.replace(tmp_path, cache_path)
    except OSError:  # pragma: no cover - read-only install, cache disabled.
        pass

    return manifest, collisions


def _scan_manifest(package_dir: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """AST-scan ``package_dir`` and build the discovery manifest.

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
        # Skip infrastructure modules and any private (underscore-prefixed)
        # module so internal/experimental code does not leak into the public
        # surface by convention.
        if module_name in _SKIP_MODULES or module_name.startswith("_"):
            continue

        path = os.path.join(package_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                source = fh.read()
        except OSError:  # pragma: no cover - defensive
            continue

        for symbol in _iter_public_symbols(source, module_name):
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
