"""Tool discovery / catalogue contract for PraisonAI Tools.

This module provides a single, programmatic way to enumerate every tool that
``praisonai-tools`` ships, plus any third-party tool registered via the
``praisonai.tools`` entry-point group. It exists so that the wider SDK (CLI,
docs, YAML validators, third-party packages) can answer *"what tools can I
actually use here?"* against a live catalogue derived from the real registry
rather than a hand-maintained allowlist that drifts.

Usage:
    from praisonai_tools import list_tools

    for entry in list_tools():
        print(entry.name, entry.module, entry.extras, entry.summary)

Third-party packages can register their own tools by declaring an entry point:

    # pyproject.toml (third-party tool package)
    [project.entry-points."praisonai.tools"]
    my_tool = "my_pkg:MyTool"

Nothing here imports optional/heavy dependencies: the catalogue is built from
the module map alone, so ``list_tools()`` is safe to call without any extras
installed.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, Optional, Tuple

ENTRY_POINT_GROUP = "praisonai.tools"

# Directory that holds the first-party ``*_tool.py`` files. The catalogue is
# derived by scanning this directory, so dropping a new ``*_tool.py`` that
# defines a ``*Tool`` class makes the tool discoverable with no edits to any
# hand-maintained list.
_TOOLS_DIR = os.path.join(os.path.dirname(__file__), "tools")

# Map from the module (as recorded in ``_TOOL_MAP``) to the optional-dependency
# extras required to use tools defined in it. Modules absent from this mapping
# have no extra requirements (they rely only on the standard library or on the
# base dependencies). Keep this aligned with ``[project.optional-dependencies]``
# in ``pyproject.toml``.
_MODULE_EXTRAS = {
    "wordpress_tool": ("wordpress",),
    "pinchwork_tool": ("pinchwork", "marketplace"),
    "agentid_tool": ("agentid", "marketplace"),
    "joy_trust_tool": ("joy-trust", "marketplace"),
    "agentfolio_tool": ("agentfolio", "marketplace"),
    "praisonai_tools.n8n.n8n_workflow": ("n8n",),
    "langextract_tool": ("langextract",),
    "swarmscore_tool": ("swarmscore",),
    "composio_tool": ("composio",),
}


@dataclass(frozen=True)
class ToolCatalogueEntry:
    """A single discoverable tool.

    Attributes:
        name: Public name used to import/reference the tool, e.g. ``"QdrantTool"``.
        module: Dotted or relative module path that defines the tool.
        extras: Optional-dependency extras required to use the tool, e.g.
            ``("swarmscore",)``. Empty when no extra install is needed.
        summary: A one-line human-readable description of the tool.
    """

    name: str
    module: str
    extras: Tuple[str, ...] = field(default_factory=tuple)
    summary: str = ""


def _summary_for(name: str) -> str:
    """Derive a concise one-line summary for a tool class name.

    Fallback used only when a tool class does not declare a literal
    ``description``. We avoid importing the tool (which could pull heavy/optional
    deps) and instead produce a stable, human-friendly summary from the name.
    """
    if name.endswith("Tool"):
        base = name[:-4]
    else:
        base = name
    return f"{base} integration tool".strip()


def _first_line(text: str) -> str:
    """Return the first non-empty line of ``text`` (a tool ``description``)."""
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def _scan_module(path: str) -> "list[tuple[str, str]]":
    """AST-scan a ``*_tool.py`` file for ``*Tool`` classes and descriptions.

    Returns a list of ``(class_name, summary)`` tuples. The file is parsed, not
    imported, so this stays cheap and never triggers optional dependencies.
    Classes without a literal ``description`` fall back to a name-synthesised
    summary.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
    except (OSError, SyntaxError):  # pragma: no cover - defensive
        return []

    found = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or not node.name.endswith("Tool"):
            continue
        description: Optional[str] = None
        for stmt in node.body:
            # Accept both plain ``description = "..."`` and annotated
            # ``description: str = "..."`` class attributes.
            if isinstance(stmt, ast.Assign):
                targets = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
                value = stmt.value
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                targets = [stmt.target.id]
                value = stmt.value
            else:
                continue
            if (
                "description" in targets
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                description = value.value
        summary = _first_line(description) if description else _summary_for(node.name)
        found.append((node.name, summary or _summary_for(node.name)))
    return found


@lru_cache(maxsize=1)
def _scan_source_tree() -> "Dict[str, Tuple[str, str]]":
    """Derive the first-party tool catalogue from the source tree.

    Scans every ``praisonai_tools/tools/*_tool.py`` file for ``*Tool`` classes
    and returns ``{class_name: (module, summary)}``. Because the mapping is
    derived from the files that actually exist, phantom names (advertised tools
    with no file) are impossible by construction, and adding a tool is a single
    new-file change.
    """
    derived: "Dict[str, Tuple[str, str]]" = {}
    try:
        filenames = sorted(os.listdir(_TOOLS_DIR))
    except OSError:  # pragma: no cover - defensive
        return derived

    for filename in filenames:
        if not filename.endswith("_tool.py"):
            continue
        module = filename[:-3]  # strip ".py"; relative module name within tools
        path = os.path.join(_TOOLS_DIR, filename)
        for class_name, summary in _scan_module(path):
            derived.setdefault(class_name, (module, summary))
    return derived


def _first_party_entries() -> "list[ToolCatalogueEntry]":
    """Build catalogue entries for every first-party tool class.

    The catalogue is source-derived: it is built by scanning the actual
    ``*_tool.py`` files on disk (see ``_scan_source_tree``) rather than a
    hand-maintained dictionary, so it can never advertise a tool whose file does
    not exist. Summaries come from each tool's own ``description``.

    A few tools live in nested packages (e.g. the n8n workflow tool under
    ``praisonai_tools.n8n``) rather than flat ``*_tool.py`` files; those are
    still surfaced via ``_TOOL_MAP`` so their public names remain stable.
    """
    entries: "Dict[str, ToolCatalogueEntry]" = {}

    for name, (module, summary) in _scan_source_tree().items():
        entries[name] = ToolCatalogueEntry(
            name=name,
            module=module,
            extras=_MODULE_EXTRAS.get(module, ()),
            summary=summary,
        )

    # Include tool classes defined outside the flat ``*_tool.py`` layout (e.g.
    # nested subpackages such as ``praisonai_tools.n8n``) that the scan cannot
    # reach, keeping their names stable. Only *nested* (absolute-module) tools
    # are merged here: flat ``*_tool.py`` classes are already source-derived by
    # the scan above, so restoring them from ``_TOOL_MAP`` would reintroduce the
    # hand-maintained bookkeeping this catalogue exists to eliminate.
    try:
        from praisonai_tools.tools import _TOOL_MAP
    except Exception:  # pragma: no cover - defensive
        _TOOL_MAP = {}
    for name, module in _TOOL_MAP.items():
        if not name.endswith("Tool") or name in entries:
            continue
        if not module.startswith("praisonai_tools."):
            continue
        entries[name] = ToolCatalogueEntry(
            name=name,
            module=module,
            extras=_MODULE_EXTRAS.get(module, ()),
            summary=_summary_for(name),
        )

    return list(entries.values())


def _entry_point_entries() -> "list[ToolCatalogueEntry]":
    """Build catalogue entries for third-party tools registered via entry points.

    Third-party packages register under the ``praisonai.tools`` entry-point
    group. We do not import the target object (to keep discovery cheap and
    dependency-free); we record the declared name and module value instead.
    """
    try:
        from importlib.metadata import entry_points
    except ImportError:  # pragma: no cover - Python < 3.8
        return []

    entries = []
    try:
        eps = entry_points()
        # importlib.metadata API differs across versions.
        if hasattr(eps, "select"):
            selected = eps.select(group=ENTRY_POINT_GROUP)
        else:  # pragma: no cover - Python < 3.10 dict interface
            selected = eps.get(ENTRY_POINT_GROUP, [])
    except Exception:  # pragma: no cover - defensive
        return []

    for ep in selected:
        entries.append(
            ToolCatalogueEntry(
                name=ep.name,
                module=getattr(ep, "value", "") or "",
                extras=(),
                summary=f"Third-party tool registered via {ENTRY_POINT_GROUP}",
            )
        )
    return entries


def list_tools() -> "list[ToolCatalogueEntry]":
    """Return the full catalogue of available tools.

    Includes every first-party tool shipped with ``praisonai-tools`` plus any
    third-party tool registered via the ``praisonai.tools`` entry-point group.
    Entries are de-duplicated by name (first-party wins) and returned sorted by
    name.
    """
    seen = {}
    for entry in _first_party_entries():
        seen[entry.name] = entry
    for entry in _entry_point_entries():
        seen.setdefault(entry.name, entry)
    return sorted(seen.values(), key=lambda e: e.name)


def get_tool_names() -> "set[str]":
    """Return the set of every available tool name.

    Convenience helper for validators that only need membership checks (e.g. to
    replace a hand-maintained allowlist).
    """
    return {entry.name for entry in list_tools()}
