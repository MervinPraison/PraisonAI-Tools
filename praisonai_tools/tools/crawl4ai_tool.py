"""Crawl4AI Tool for PraisonAI Agents.

Web crawling and scraping using Crawl4AI.

Usage:
    from praisonai_tools import Crawl4AITool
    
    crawler = Crawl4AITool()
    content = crawler.crawl("https://example.com")
"""

import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class Crawl4AITool(BaseTool):
    """Tool for web crawling using Crawl4AI."""
    
    name = "crawl4ai"
    description = "Crawl and extract content from websites."
    
    def __init__(self):
        super().__init__()
    
    def run(
        self,
        action: str = "crawl",
        url: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        action = action.lower().replace("-", "_")
        
        if action == "crawl":
            return self.crawl(url=url, **kwargs)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def crawl(self, url: str, extract_markdown: bool = True) -> Dict[str, Any]:
        """Crawl a URL and extract content."""
        if not url:
            return {"error": "url is required"}
        
        try:
            from crawl4ai import WebCrawler
        except ImportError:
            return {"error": "crawl4ai not installed. Install with: pip install crawl4ai"}
        
        try:
            crawler = WebCrawler()
            crawler.warmup()
            
            result = crawler.run(url=url)
            
            return {
                "url": url,
                "success": result.success,
                "markdown": result.markdown[:5000] if result.markdown else "",
                "title": result.metadata.get("title") if result.metadata else None,
            }
        except Exception as e:
            logger.error(f"Crawl4AI crawl error: {e}")
            return {"error": str(e)}


def crawl4ai_crawl(url: str) -> Dict[str, Any]:
    """Crawl URL with Crawl4AI."""
    return Crawl4AITool().crawl(url=url)
