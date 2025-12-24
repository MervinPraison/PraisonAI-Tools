"""Oxylabs Tool for PraisonAI Agents.

Web scraping using Oxylabs.

Usage:
    from praisonai_tools import OxylabsTool
    
    oxy = OxylabsTool()
    content = oxy.scrape("https://example.com")

Environment Variables:
    OXYLABS_USERNAME: Oxylabs username
    OXYLABS_PASSWORD: Oxylabs password
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class OxylabsTool(BaseTool):
    """Tool for Oxylabs web scraping."""
    
    name = "oxylabs"
    description = "Web scraping using Oxylabs."
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.username = username or os.getenv("OXYLABS_USERNAME")
        self.password = password or os.getenv("OXYLABS_PASSWORD")
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
        """Scrape URL."""
        if not url:
            return {"error": "url is required"}
        if not self.username or not self.password:
            return {"error": "OXYLABS_USERNAME and OXYLABS_PASSWORD required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            payload = {"source": "universal", "url": url}
            resp = requests.post(
                "https://realtime.oxylabs.io/v1/queries",
                auth=(self.username, self.password),
                json=payload,
                timeout=60,
            )
            data = resp.json()
            results = data.get("results", [{}])
            return {
                "url": url,
                "content": results[0].get("content", "") if results else "",
            }
        except Exception as e:
            logger.error(f"Oxylabs scrape error: {e}")
            return {"error": str(e)}


def oxylabs_scrape(url: str) -> Dict[str, Any]:
    """Scrape with Oxylabs."""
    return OxylabsTool().scrape(url=url)
