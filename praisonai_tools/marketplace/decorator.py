"""Minimal tool decorator for marketplace tools."""

from typing import Callable, Any
from functools import wraps


def tool(func: Callable[..., Any]) -> Callable[..., Any]:
    """Minimal @tool decorator for marketplace tools.
    
    This is a standalone decorator that doesn't require praisonaiagents.
    The full praisonaiagents.tools.decorator will override this when available.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Mark as a tool for agent discovery
    wrapper._is_tool = True
    wrapper._tool_name = func.__name__
    wrapper._tool_description = func.__doc__ or ""
    
    return wrapper