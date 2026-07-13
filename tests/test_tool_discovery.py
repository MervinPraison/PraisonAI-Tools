"""Regression tests for automatic tool discovery.

These guard the "shipped but not importable" gap: every public tool symbol that
ships under ``praisonai_tools/tools/`` must be reachable through both public
import surfaces, and adding a new tool module must require no other edits.
"""

import ast
import importlib
import os

import pytest

import praisonai_tools
from praisonai_tools import tools as tools_pkg
from praisonai_tools.tools._discovery import (
    build_manifest,
    _iter_public_symbols,
    _SKIP_MODULES,
)

TOOLS_DIR = os.path.dirname(tools_pkg.__file__)


def _public_symbols(path):
    with open(path, "r", encoding="utf-8") as fh:
        source = fh.read()
    return _iter_public_symbols(source, os.path.basename(path)[:-3])


def _tool_modules():
    for filename in sorted(os.listdir(TOOLS_DIR)):
        module_name = filename[:-3]
        if (
            filename.endswith(".py")
            and module_name not in _SKIP_MODULES
            and not module_name.startswith("_")
        ):
            yield module_name


def test_no_discovery_collisions():
    _, collisions = build_manifest(TOOLS_DIR)
    assert collisions == {}, f"Colliding tool symbols across modules: {collisions}"


def test_manifest_covers_every_shipped_symbol():
    manifest, _ = build_manifest(TOOLS_DIR)
    for module in _tool_modules():
        path = os.path.join(TOOLS_DIR, module + ".py")
        for symbol in _public_symbols(path):
            assert symbol in manifest, (
                f"{symbol!r} defined in tools/{module}.py is not discoverable"
            )


def test_all_matches_manifest():
    manifest, _ = build_manifest(TOOLS_DIR)
    base = {
        "BaseTool", "ToolResult", "ToolValidationError", "validate_tool",
        "tool", "FunctionTool", "is_tool", "get_tool_schema",
    }
    expected = base | set(manifest)
    assert set(tools_pkg.__all__) == expected
    # Top-level package mirrors the tools package surface.
    assert set(praisonai_tools.__all__) == set(tools_pkg.__all__)


@pytest.mark.parametrize("name", [
    "EmailTool", "SlackTool", "GitHubTool", "WeatherTool", "YouTubeTool",
    "send_email", "get_weather", "search_youtube",
    # Symbol from a module that declares an explicit __all__ (author intent).
    "NexusPredictionMarketTool",
    # External symbol living outside tools/ (exercises the absolute-path
    # import branch in __getattr__ and the _EXTERNAL_SYMBOLS mapping).
    "N8nWorkflowTool",
])
def test_known_symbols_resolve_both_surfaces(name):
    assert getattr(tools_pkg, name) is getattr(praisonai_tools, name)


def test_explicit_all_is_respected():
    """A module declaring __all__ contributes exactly those public names."""
    manifest, _ = build_manifest(TOOLS_DIR)
    # nexus_prediction_market_tool.py declares __all__ with these two names.
    assert manifest.get("NexusPredictionMarketTool") == "nexus_prediction_market_tool"
    assert manifest.get("nexus_prediction_market_tool") == "nexus_prediction_market_tool"


def test_lazy_import_not_eager(monkeypatch):
    """Importing the package must not eagerly import a heavy tool module."""
    import sys

    # A representative heavy/optional tool module should not be imported until
    # one of its symbols is accessed.
    target = "praisonai_tools.tools.docker_tool"
    sys.modules.pop(target, None)
    importlib.reload(tools_pkg)
    assert target not in sys.modules
    # Accessing a symbol triggers the lazy import.
    _ = tools_pkg.DockerTool
    assert target in sys.modules


def test_drop_in_new_tool(tmp_path, monkeypatch):
    """A new module dropped into tools/ is importable with no other edits."""
    if not os.access(TOOLS_DIR, os.W_OK):
        pytest.skip("TOOLS_DIR is not writable (read-only install)")
    echo_path = os.path.join(TOOLS_DIR, "echo_discovery_probe.py")
    source = (
        "from praisonai_tools.tools.decorator import tool\n\n\n"
        "@tool\n"
        "def echo_discovery_probe(text: str) -> str:\n"
        "    '''Echo the given text.'''\n"
        "    return text\n"
    )
    with open(echo_path, "w", encoding="utf-8") as fh:
        fh.write(source)
    try:
        importlib.reload(tools_pkg)
        fn = tools_pkg.echo_discovery_probe
        assert fn("hi") == "hi"
        assert "echo_discovery_probe" in tools_pkg.__all__
    finally:
        os.remove(echo_path)
        importlib.reload(tools_pkg)


def test_manifest_cache_roundtrip(tmp_path):
    """The disk cache is written, reused, and invalidated on directory change."""
    from praisonai_tools.tools import _discovery

    pkg = tmp_path / "toolsdir"
    pkg.mkdir()
    (pkg / "sample_tool.py").write_text("class SampleTool:\n    pass\n")

    manifest, _ = _discovery.build_manifest(str(pkg))
    assert manifest.get("SampleTool") == "sample_tool"
    cache_file = pkg / _discovery._CACHE_FILENAME
    assert cache_file.exists(), "cache should be written after first scan"

    # Second call must serve from cache (fingerprint unchanged) and match.
    manifest2, _ = _discovery.build_manifest(str(pkg))
    assert manifest2 == manifest

    # Adding a module changes the fingerprint -> cache is rebuilt automatically.
    (pkg / "second_tool.py").write_text("def second_tool():\n    return 1\n")
    manifest3, _ = _discovery.build_manifest(str(pkg))
    assert "second_tool" in manifest3


def test_manifest_cache_corrupt_falls_back(tmp_path):
    """A corrupt cache file must not break discovery."""
    from praisonai_tools.tools import _discovery

    pkg = tmp_path / "toolsdir"
    pkg.mkdir()
    (pkg / "sample_tool.py").write_text("class SampleTool:\n    pass\n")
    (pkg / _discovery._CACHE_FILENAME).write_text("{ not valid json")

    manifest, _ = _discovery.build_manifest(str(pkg))
    assert manifest.get("SampleTool") == "sample_tool"
