"""Tools package for PraisonAI Tools.

This module provides base classes and ready-to-use tools for AI agents.

Base classes for custom tools:
- BaseTool, @tool decorator, FunctionTool

Ready-to-use tools:
- EmailTool: Send/read emails via SMTP/IMAP
- SlackTool: Send messages to Slack
- DiscordTool: Send messages to Discord
- GitHubTool: Interact with GitHub repos/issues
- ImageTool: Generate images with DALL-E
- WeatherTool: Get weather data
- YouTubeTool: Search YouTube, get transcripts
- TTSTool: Text-to-speech conversion

Tools are discovered automatically: adding a module under
``praisonai_tools/tools/`` exposes its public top-level classes and functions
without any manual registration. Imports remain lazy - a tool module (and its
optional dependencies) is only imported the first time one of its symbols is
accessed.
"""

import os

from praisonai_tools.tools.base import BaseTool, ToolResult, ToolValidationError, validate_tool
from praisonai_tools.tools.decorator import tool, FunctionTool, is_tool, get_tool_schema
from praisonai_tools.tools._discovery import build_manifest

# Symbols exported eagerly above (base classes + decorator helpers).
_BASE_EXPORTS = [
    "BaseTool",
    "ToolResult",
    "ToolValidationError",
    "validate_tool",
    "tool",
    "FunctionTool",
    "is_tool",
    "get_tool_schema",
]

# Build the discovery manifest once at import time. This only reads/parses
# source files (via AST) - it does NOT import any tool module, so lazy loading
# of heavy optional dependencies is preserved.
_TOOL_MANIFEST, _COLLISIONS = build_manifest(os.path.dirname(__file__))


def __getattr__(name):
    """Lazily import a discovered tool symbol on first access."""
    module_name = _TOOL_MANIFEST.get(name)
    if module_name is not None:
        from importlib import import_module

        if module_name.startswith("praisonai_tools."):
            module = import_module(module_name)
        else:
            module = import_module(f".{module_name}", __package__)
        return getattr(module, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(_BASE_EXPORTS) | set(_TOOL_MANIFEST))


# ``__all__`` is derived from the same manifest as ``__getattr__`` so the two
# can never drift apart.
__all__ = sorted(set(_BASE_EXPORTS) | set(_TOOL_MANIFEST))
