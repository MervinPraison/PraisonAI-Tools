"""Tool decorator for converting functions into tools.

This module re-exports the @tool decorator and related utilities from praisonaiagents.
This ensures a single source of truth for the tool decorator infrastructure.

Usage:
    from praisonai_tools import tool

    @tool
    def search(query: str) -> list:
        '''Search the web for information.'''
        return [...]

    # Or with explicit parameters:
    @tool(name="web_search", description="Search the internet")
    def search(query: str, max_results: int = 5) -> list:
        return [...]
"""

import logging as _logging


class _SuppressRegistryNoneWarning(_logging.Filter):
    """Drop the benign "Registry is None for tool …" WARNING.

    ``praisonaiagents.tools.decorator`` logs a WARNING for every ``@tool``
    decorated function when no global tool registry exists yet. On a bare
    ``import`` (library use, scripts, pytest collection) that is the normal
    state, not an anomaly - registration happens lazily once an agent/registry
    comes up. The message fires once per decorated function, so the noise scales
    with the tool catalogue and is the first thing every consumer sees. We drop
    only that specific record and leave all other logging untouched.
    """

    def filter(self, record: _logging.LogRecord) -> bool:
        return not record.getMessage().startswith("Registry is None for tool")


def _silence_registry_none_warning() -> None:
    """Install the filter so bare imports stay quiet at default log levels.

    The upstream code emits the record via ``logging.warning`` (the root
    logger), and ``praisonaiagents`` configures a handler on the root logger, so
    the record surfaces there. We attach the filter to the root logger and its
    handlers - it only drops the single "Registry is None for tool …" record and
    passes everything else through, so user logging is unaffected. The proper fix
    (defer registration / downgrade to debug) belongs in praisonaiagents core.
    """
    filt = _SuppressRegistryNoneWarning()
    root = _logging.getLogger()
    root.addFilter(filt)
    for handler in root.handlers:
        handler.addFilter(filt)


# ``praisonaiagents`` configures root logging on import; do it first so its
# handlers exist, then attach the filter before any module-level ``@tool``
# decoration runs.
import praisonaiagents  # noqa: F401  (import for logging side effects only)

_silence_registry_none_warning()

# Import from praisonaiagents - single source of truth
from praisonaiagents.tools.decorator import (
    tool,
    FunctionTool,
    is_tool,
    get_tool_schema,
)

__all__ = [
    "tool",
    "FunctionTool",
    "is_tool",
    "get_tool_schema",
]
