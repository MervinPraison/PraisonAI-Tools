"""BrightData Tool for PraisonAI Agents.

Web scraping using BrightData proxy network.

Usage:
    from praisonai_tools import BrightDataTool
    
    bd = BrightDataTool()
    content = bd.scrape("https://example.com")

Environment Variables:
    BRIGHTDATA_USERNAME: BrightData username
    BRIGHTDATA_PASSWORD: BrightData password
    BRIGHTDATA_HOST: BrightData proxy host
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class BrightDataTool(BaseTool):
    """Tool for BrightData web scraping."""
    
    name = "brightdata"
    description = "Web scraping using BrightData proxy network."
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
    ):
        self.username = username or os.getenv("BRIGHTDATA_USERNAME")
        self.password = password or os.getenv("BRIGHTDATA_PASSWORD")
        self.host = host or os.getenv("BRIGHTDATA_HOST", "brd.superproxy.io:22225")
        super().__init__()
    
    def run(
        self,
        action: str = "scrape",
        url: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "scrape":
            return self.scrape(url=url)
        return {"error": f"Unknown action: {action}"}
    
    def scrape(self, url: str) -> Dict[str, Any]:
        """Scrape URL through BrightData proxy."""
        if not url:
            return {"error": "url is required"}
        if not self.username or not self.password:
            return {"error": "BRIGHTDATA_USERNAME and BRIGHTDATA_PASSWORD required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            proxy = f"http://{self.username}:{self.password}@{self.host}"
            proxies = {"http": proxy, "https": proxy}
            resp = requests.get(url, proxies=proxies, timeout=30, verify=False)
            return {
                "url": url,
                "status_code": resp.status_code,
                "content": resp.text[:10000],
            }
        except Exception as e:
            logger.error(f"BrightData scrape error: {e}")
            return {"error": str(e)}


def brightdata_scrape(url: str) -> Dict[str, Any]:
    """Scrape with BrightData."""
    return BrightDataTool().scrape(url=url)
