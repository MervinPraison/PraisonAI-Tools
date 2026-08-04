"""CI-covered guard for automatic tool discovery.

The full discovery regression suite lives at ``tests/test_tool_discovery.py``,
but the CI workflow only runs ``pytest tests/unit --ignore=tests/unit/video``.
That means the most important safety net there - proving every shipped tool
module actually parses (so discovery never silently drops a tool) - would not
execute in CI. This thin module re-runs that guard from inside the CI-covered
path so a syntactically broken shipped module fails loudly at CI time with the
pointing ``SyntaxError`` instead of surfacing later as a mystery
``AttributeError`` on ``from praisonai_tools import SomeTool``.
"""

import ast
import os

import pytest

from praisonai_tools import tools as tools_pkg
from praisonai_tools.tools._discovery import _SKIP_MODULES, build_manifest

TOOLS_DIR = os.path.dirname(tools_pkg.__file__)


def _tool_modules():
    for filename in sorted(os.listdir(TOOLS_DIR)):
        module_name = filename[:-3]
        if (
            filename.endswith(".py")
            and module_name not in _SKIP_MODULES
            and not module_name.startswith("_")
        ):
            yield module_name


def test_every_shipped_module_parses_in_ci():
    """Every shipped tool module must parse under the running interpreter."""
    for module in _tool_modules():
        path = os.path.join(TOOLS_DIR, module + ".py")
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
        try:
            ast.parse(source)
        except SyntaxError as exc:  # pragma: no cover - fails only if a module breaks
            pytest.fail(f"tools/{module}.py has a syntax error: {exc}")


def test_no_discovery_collisions_in_ci():
    """No public tool symbol may be defined in two shipped modules."""
    _, collisions = build_manifest(TOOLS_DIR)
    assert collisions == {}, f"Colliding tool symbols across modules: {collisions}"
