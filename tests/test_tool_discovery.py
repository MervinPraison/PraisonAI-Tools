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
from praisonai_tools.tools._discovery import build_manifest, _SKIP_MODULES

TOOLS_DIR = os.path.dirname(tools_pkg.__file__)


def _public_symbols(path):
    with open(path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and not node.name.startswith("_")
    ]


def _tool_modules():
    for filename in sorted(os.listdir(TOOLS_DIR)):
        if filename.endswith(".py") and filename[:-3] not in _SKIP_MODULES:
            yield filename[:-3]


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
])
def test_known_symbols_resolve_both_surfaces(name):
    assert getattr(tools_pkg, name) is getattr(praisonai_tools, name)


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
    echo_path = os.path.join(TOOLS_DIR, "_echo_discovery_probe.py")
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
