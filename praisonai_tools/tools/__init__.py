"""Tools package for PraisonAI Tools.

This module provides lazy loading of all available tools.
"""

from praisonai_tools.tools.base import BaseTool, ToolResult, ToolValidationError
from praisonai_tools.tools.decorator import tool, FunctionTool

# Tavily Tools
from praisonai_tools.tools.tavily_tools import (
    TavilyTools,
    tavily_search,
    tavily_extract,
    tavily_crawl,
    tavily_map,
)

# Exa Tools
from praisonai_tools.tools.exa_tools import (
    ExaTools,
    exa_search,
    exa_search_contents,
    exa_find_similar,
    exa_answer,
)

# You.com Tools
from praisonai_tools.tools.youdotcom_tools import (
    YouTools,
    ydc_search,
    ydc_contents,
    ydc_news,
    ydc_images,
)

__all__ = [
    # Base
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
