"""PraisonAI Tools - Tools and base classes for AI agents.

This package provides:
1. Base classes for creating custom tools (BaseTool, @tool decorator)
2. Ready-to-use tools for common tasks (Email, Slack, GitHub, etc.)

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
    
    # Method 3: Use built-in tools
    from praisonai_tools import EmailTool, SlackTool, GitHubTool
    
    email = EmailTool(provider="gmail")
    slack = SlackTool()
    github = GitHubTool()
    
    # Use with PraisonAI Agents
    from praisonaiagents import Agent
    agent = Agent(tools=[my_search, MyTool(), email, slack])
"""

from importlib.metadata import version, PackageNotFoundError

from praisonai_tools.tools.base import BaseTool, ToolResult, ToolValidationError, validate_tool
from praisonai_tools.tools.decorator import tool, FunctionTool, is_tool, get_tool_schema

# ``__all__`` is derived from the tools package's automatically-discovered
# manifest so the two levels cannot drift apart. Only source files are parsed
# (via AST) to build it - no tool module is eagerly imported here.
from praisonai_tools.tools import __all__ as _tools_all

try:
    __version__ = version("praisonai-tools")
except PackageNotFoundError:
    __version__ = "0.0.0"
__author__ = "Mervin Praison"

# Lazy imports for tool classes
def __getattr__(name):
    """Lazy load tool classes to avoid loading dependencies until needed."""
    from praisonai_tools.tools import __getattr__ as tools_getattr
    try:
        return tools_getattr(name)
    except AttributeError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = list(_tools_all)


def __dir__():
    return sorted(set(globals()) | set(__all__))