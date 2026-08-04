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

from dataclasses import dataclass, field
from typing import Tuple

ENTRY_POINT_GROUP = "praisonai.tools"

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

    We avoid importing the tool (which could pull heavy/optional deps) and
    instead produce a stable, human-friendly summary from the name itself.
    """
    if name.endswith("Tool"):
        base = name[:-4]
    else:
        base = name
    return f"{base} integration tool".strip()


def _first_party_entries() -> "list[ToolCatalogueEntry]":
    """Build catalogue entries for every first-party tool class.

    The source of truth is ``praisonai_tools.tools._TOOL_MAP`` which maps every
    public name (both classes and helper functions) to its defining module. We
    expose only the tool *classes* (names ending in ``Tool``) in the catalogue,
    since those are what ``agents.yaml`` and the SDK reference.
    """
    from praisonai_tools.tools import _TOOL_MAP

    entries = []
    for name, module in sorted(_TOOL_MAP.items()):
        if not name.endswith("Tool"):
            continue
        extras = _MODULE_EXTRAS.get(module, ())
        entries.append(
            ToolCatalogueEntry(
                name=name,
                module=module,
                extras=extras,
                summary=_summary_for(name),
            )
        )
    return entries


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
