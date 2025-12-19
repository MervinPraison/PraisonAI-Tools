"""PraisonAI Tools - A comprehensive toolkit for AI agents.

This package provides a collection of tools that can be used with PraisonAI agents
for web search, content extraction, file operations, and more.

Usage:
    from praisonai_tools import (
        # Search tools
        tavily_search, exa_search, ydc_search,
        
        # Tool classes
        TavilyTools, ExaTools, YouTools,
        
        # Base classes for custom tools
        BaseTool, tool
    )
"""

from praisonai_tools.tools.base import BaseTool, ToolResult, ToolValidationError
from praisonai_tools.tools.decorator import tool, FunctionTool

# Import all tools
from praisonai_tools.tools import (
    # Tavily Tools
    TavilyTools,
    tavily_search,
    tavily_extract,
    tavily_crawl,
    tavily_map,
    
    # Exa Tools
    ExaTools,
    exa_search,
    exa_search_contents,
    exa_find_similar,
    exa_answer,
    
    # You.com Tools
    YouTools,
    ydc_search,
    ydc_contents,
    ydc_news,
    ydc_images,
)

__version__ = "0.1.0"
__author__ = "Mervin Praison"

__all__ = [
    # Base classes
    "BaseTool",
    "ToolResult", 
    "ToolValidationError",
    "tool",
    "FunctionTool",
    
    # Tavily
    "TavilyTools",
    "tavily_search",
    "tavily_extract",
    "tavily_crawl",
    "tavily_map",
    
    # Exa
    "ExaTools",
    "exa_search",
    "exa_search_contents",
    "exa_find_similar",
    "exa_answer",
    
    # You.com
    "YouTools",
    "ydc_search",
    "ydc_contents",
    "ydc_news",
    "ydc_images",
]