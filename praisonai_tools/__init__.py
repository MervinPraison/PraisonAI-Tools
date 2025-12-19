"""PraisonAI Tools - Base classes for creating custom tools for AI agents.

This package provides the foundation for creating custom tools that work with
PraisonAI Agents. Use BaseTool or the @tool decorator to create your own tools.

Note: Common tools (Tavily, Exa, You.com, DuckDuckGo, Wikipedia, etc.) are 
already built into praisonaiagents. This package is for creating CUSTOM tools.

Usage:
    from praisonai_tools import BaseTool, tool
    
    # Method 1: Using @tool decorator
    @tool
    def my_search(query: str) -> str:
        '''Search for something.'''
        return f"Results for {query}"
    
    # Method 2: Subclassing BaseTool
    class MyTool(BaseTool):
        name = "my_tool"
        description = "Does something useful"
        
        def run(self, query: str) -> str:
            return f"Result for {query}"
    
    # Use with PraisonAI Agents
    from praisonaiagents import Agent
    agent = Agent(tools=[my_search, MyTool()])
"""

from praisonai_tools.tools.base import BaseTool, ToolResult, ToolValidationError, validate_tool
from praisonai_tools.tools.decorator import tool, FunctionTool, is_tool, get_tool_schema

__version__ = "0.1.0"
__author__ = "Mervin Praison"

__all__ = [
    # Base classes for custom tools
    "BaseTool",
    "ToolResult", 
    "ToolValidationError",
    "validate_tool",
    
    # Decorator for function-based tools
    "tool",
    "FunctionTool",
    "is_tool",
    "get_tool_schema",
]