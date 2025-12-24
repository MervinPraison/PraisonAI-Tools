"""Firecrawl Tool for PraisonAI Agents.

Web scraping and crawling using Firecrawl API.

Usage:
    from praisonai_tools import FirecrawlTool
    
    fc = FirecrawlTool()
    content = fc.scrape("https://example.com")

Environment Variables:
    FIRECRAWL_API_KEY: Firecrawl API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class FirecrawlTool(BaseTool):
    """Tool for web scraping using Firecrawl."""
    
    name = "firecrawl"
    description = "Scrape and crawl websites using Firecrawl."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("FIRECRAWL_API_KEY is required")
            try:
                from firecrawl import FirecrawlApp
            except ImportError:
                raise ImportError("firecrawl-py not installed. Install with: pip install firecrawl-py")
            self._client = FirecrawlApp(api_key=self.api_key)
        return self._client
    
    def run(
        self,
        action: str = "scrape",
        url: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "scrape":
            return self.scrape(url=url, **kwargs)
        elif action == "crawl":
            return self.crawl(url=url, **kwargs)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def scrape(self, url: str, formats: List[str] = None) -> Dict[str, Any]:
        """Scrape a single URL."""
        if not url:
            return {"error": "url is required"}
        
        if not self.api_key:
            return {"error": "FIRECRAWL_API_KEY not configured"}
        
        try:
            params = {}
            if formats:
                params["formats"] = formats
            
            result = self.client.scrape_url(url, params=params if params else None)
            
            return {
                "url": url,
                "markdown": result.get("markdown", "")[:5000],
                "metadata": result.get("metadata", {}),
            }
        except Exception as e:
            logger.error(f"Firecrawl scrape error: {e}")
            return {"error": str(e)}
    
    def crawl(self, url: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Crawl a website."""
        if not url:
            return [{"error": "url is required"}]
        
        if not self.api_key:
            return [{"error": "FIRECRAWL_API_KEY not configured"}]
        
        try:
            result = self.client.crawl_url(
                url,
                params={"limit": limit},
                poll_interval=5,
            )
            
            pages = []
            for page in result.get("data", [])[:limit]:
                pages.append({
                    "url": page.get("metadata", {}).get("sourceURL"),
                    "title": page.get("metadata", {}).get("title"),
                    "markdown": page.get("markdown", "")[:2000],
                })
            return pages
        except Exception as e:
            logger.error(f"Firecrawl crawl error: {e}")
            return [{"error": str(e)}]


def firecrawl_scrape(url: str) -> Dict[str, Any]:
    """Scrape URL with Firecrawl."""
    return FirecrawlTool().scrape(url=url)
