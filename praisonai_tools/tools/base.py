"""Base classes for PraisonAI Tools.

This module re-exports BaseTool and related classes from praisonaiagents.
This ensures a single source of truth for the base tool infrastructure.

Usage:
    from praisonai_tools import BaseTool

    class MyTool(BaseTool):
        name = "my_tool"
        description = "Does something useful"
        
        def run(self, query: str) -> str:
            return f"Result for {query}"
"""

# Import from praisonaiagents - single source of truth
from praisonaiagents.tools.base import (
    BaseTool,
    ToolResult,
    ToolValidationError,
    validate_tool,
)

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolValidationError",
    "validate_tool",
]
