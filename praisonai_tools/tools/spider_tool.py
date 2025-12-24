"""Spider Tool for PraisonAI Agents.

Web crawling using Spider API.

Usage:
    from praisonai_tools import SpiderTool
    
    spider = SpiderTool()
    content = spider.crawl("https://example.com")

Environment Variables:
    SPIDER_API_KEY: Spider API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SpiderTool(BaseTool):
    """Tool for Spider web crawling."""
    
    name = "spider"
    description = "Crawl websites using Spider API."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SPIDER_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "crawl",
        url: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        if action == "crawl":
            return self.crawl(url=url, **kwargs)
        elif action == "scrape":
            return self.scrape(url=url)
        return {"error": f"Unknown action: {action}"}
    
    def crawl(self, url: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Crawl website."""
        if not url:
            return [{"error": "url is required"}]
        if not self.api_key:
            return [{"error": "SPIDER_API_KEY required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {"url": url, "limit": limit}
            resp = requests.post(
                "https://api.spider.cloud/crawl",
                headers=headers,
                json=data,
                timeout=60,
            )
            return resp.json()
        except Exception as e:
            logger.error(f"Spider crawl error: {e}")
            return [{"error": str(e)}]
    
    def scrape(self, url: str) -> Dict[str, Any]:
        """Scrape single page."""
        if not url:
            return {"error": "url is required"}
        if not self.api_key:
            return {"error": "SPIDER_API_KEY required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {"url": url}
            resp = requests.post(
                "https://api.spider.cloud/scrape",
                headers=headers,
                json=data,
                timeout=30,
            )
            return resp.json()
        except Exception as e:
            logger.error(f"Spider scrape error: {e}")
            return {"error": str(e)}


def spider_crawl(url: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Crawl with Spider."""
    return SpiderTool().crawl(url=url, limit=limit)
