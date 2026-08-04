"""Tests for the tool discovery / catalogue contract."""


def test_list_tools_importable_from_top_level():
    from praisonai_tools import list_tools, ToolCatalogueEntry, get_tool_names

    assert callable(list_tools)
    assert callable(get_tool_names)
    assert ToolCatalogueEntry is not None


def test_list_tools_returns_entries():
    from praisonai_tools import list_tools
    from praisonai_tools.catalogue import ToolCatalogueEntry

    entries = list_tools()
    assert isinstance(entries, list)
    assert len(entries) > 100  # ships a large catalogue
    assert all(isinstance(e, ToolCatalogueEntry) for e in entries)


def test_entries_only_expose_tool_classes():
    from praisonai_tools import list_tools

    for entry in list_tools():
        assert entry.name.endswith("Tool"), entry.name


def test_entries_are_sorted_and_unique():
    from praisonai_tools import list_tools

    names = [e.name for e in list_tools()]
    assert names == sorted(names)
    assert len(names) == len(set(names))


def test_catalogue_derived_from_tool_map_source_of_truth():
    from praisonai_tools import list_tools
    from praisonai_tools.tools import _TOOL_MAP

    expected = {name for name in _TOOL_MAP if name.endswith("Tool")}
    actual = {e.name for e in list_tools()}
    # Every class in the map must be catalogued (third-party EPs may add more).
    assert expected <= actual


def test_previously_missing_optional_tool_is_now_discoverable():
    # QdrantTool was a valid tool absent from the wrapper's hand-maintained
    # allowlist; it must now be discoverable via the catalogue.
    from praisonai_tools import get_tool_names

    names = get_tool_names()
    assert "QdrantTool" in names


def test_extras_are_populated_for_optional_tools():
    from praisonai_tools import list_tools

    by_name = {e.name for e in list_tools()}
    entries = {e.name: e for e in list_tools()}

    assert "SwarmScoreTool" in by_name
    assert "swarmscore" in entries["SwarmScoreTool"].extras


def test_entries_have_summary_and_module():
    from praisonai_tools import list_tools

    for entry in list_tools():
        assert entry.module
        assert entry.summary


def test_list_tools_does_not_require_optional_deps():
    # Building the catalogue must not import any tool module / optional dep.
    from praisonai_tools import list_tools

    entries = list_tools()
    assert entries  # smoke: no ImportError raised
