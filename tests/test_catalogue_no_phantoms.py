"""CI guard: the catalogue must never advertise a phantom tool.

A "phantom" is a tool name surfaced by ``get_tool_names()`` / ``list_tools()``
whose class cannot be resolved because no implementation file (or class) exists.
Because the catalogue is now source-derived (see ``praisonai_tools.catalogue``),
phantoms should be impossible by construction; this test enforces that during
any future refactor.

Missing *optional dependencies* are explicitly tolerated: a tool whose file and
class exist but which needs an un-installed extra will raise ``ImportError`` /
``ModuleNotFoundError`` for the extra, not an ``AttributeError``. Only the
latter (name resolves to nothing) counts as a phantom.
"""

import importlib

import praisonai_tools
from praisonai_tools import get_tool_names, list_tools
from praisonai_tools.catalogue import _scan_source_tree


def _is_missing_optional_dependency(exc: BaseException, tool_module: str) -> bool:
    """True if the import failure is due to a missing *optional* dependency.

    A missing optional dependency raises ``ModuleNotFoundError`` for a module
    that is *not* the tool's own module. If the tool's own file were missing the
    name would simply not resolve (``AttributeError``) rather than importing and
    then failing on a third-party import.
    """
    if not isinstance(exc, ModuleNotFoundError):
        return False
    missing = getattr(exc, "name", "") or ""
    # ``tool_module`` may be relative (flat ``*_tool.py`` under
    # ``praisonai_tools.tools``) or already absolute (nested subpackages such as
    # ``praisonai_tools.n8n.n8n_workflow``). Resolve to the tool's own dotted
    # module either way so a *missing first-party* module is treated as a
    # phantom, not an optional dependency.
    own = (
        tool_module
        if tool_module.startswith("praisonai_tools.")
        else f"praisonai_tools.tools.{tool_module}"
    )
    return missing != own and not own.startswith(f"{missing}.")


def test_every_catalogue_name_resolves_or_needs_optional_dep():
    entries = {e.name: e for e in list_tools()}
    phantoms = []
    for name in sorted(get_tool_names()):
        module = entries.get(name).module if name in entries else ""
        try:
            getattr(praisonai_tools, name)
        except AttributeError as exc:
            phantoms.append((name, module, repr(exc)))
        except Exception as exc:  # ImportError / ModuleNotFoundError, etc.
            if not _is_missing_optional_dependency(exc, module):
                phantoms.append((name, module, repr(exc)))
    assert not phantoms, f"catalogue advertises unresolvable (phantom) tools: {phantoms}"


def test_no_phantom_modules_in_scan():
    """Every source-derived tool maps to a file that actually exists on disk."""
    import os

    tools_dir = os.path.join(os.path.dirname(praisonai_tools.__file__), "tools")
    for name, (module, _summary) in _scan_source_tree().items():
        path = os.path.join(tools_dir, f"{module}.py")
        assert os.path.isfile(path), f"{name} maps to missing file {module}.py"


def test_dropping_a_tool_file_is_auto_discovered():
    """Files on disk defining a *Tool class are catalogued without _TOOL_MAP edits.

    Guards the core promise of the issue: adding a tool is a single-file change.
    ``ClaudeMemoryTool``/``CrowPayTool``/``NightmarketTool`` exist on disk but
    were historically absent from ``_TOOL_MAP``; they must still be discoverable.
    """
    names = get_tool_names()
    for expected in ("ClaudeMemoryTool", "CrowPayTool", "NightmarketTool"):
        # Only assert for the ones whose files are present in this checkout.
        derived = _scan_source_tree()
        if expected in derived:
            assert expected in names, f"{expected} exists on disk but is not catalogued"


def test_summaries_come_from_real_description():
    entries = {e.name: e for e in list_tools()}
    # CalculatorTool declares a literal description; the summary must match it,
    # not the name-synthesised fallback ("Calculator integration tool").
    calc = entries.get("CalculatorTool")
    assert calc is not None
    assert calc.summary == "Perform mathematical calculations."
    assert "integration tool" not in calc.summary


def test_annotated_description_summaries_are_extracted():
    """Tools declaring ``description: str = "..."`` must surface the real text.

    ``CapsuleTool`` and ``NexusPredictionMarketTool`` use annotated assignments;
    their catalogue summaries must come from the literal, not the name-based
    fallback.
    """
    entries = {e.name: e for e in list_tools()}
    for name in ("CapsuleTool", "NexusPredictionMarketTool"):
        entry = entries.get(name)
        if entry is None:
            continue
        assert entry.summary
        assert "integration tool" not in entry.summary
