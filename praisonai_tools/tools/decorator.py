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
