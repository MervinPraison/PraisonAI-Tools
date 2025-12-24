"""BrowserBase Tool for PraisonAI Agents.

Browser automation using BrowserBase.

Usage:
    from praisonai_tools import BrowserBaseTool
    
    bb = BrowserBaseTool()
    content = bb.scrape("https://example.com")

Environment Variables:
    BROWSERBASE_API_KEY: BrowserBase API key
    BROWSERBASE_PROJECT_ID: BrowserBase project ID
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class BrowserBaseTool(BaseTool):
    """Tool for BrowserBase browser automation."""
    
    name = "browserbase"
    description = "Browser automation using BrowserBase."
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("BROWSERBASE_API_KEY")
        self.project_id = project_id or os.getenv("BROWSERBASE_PROJECT_ID")
        super().__init__()
    
    def run(
        self,
        action: str = "scrape",
        url: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "scrape":
            return self.scrape(url=url)
        elif action == "screenshot":
            return self.screenshot(url=url)
        return {"error": f"Unknown action: {action}"}
    
    def scrape(self, url: str) -> Dict[str, Any]:
        """Scrape page content."""
        if not url:
            return {"error": "url is required"}
        if not self.api_key:
            return {"error": "BROWSERBASE_API_KEY required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {"url": url, "projectId": self.project_id}
            resp = requests.post(
                "https://api.browserbase.com/v1/scrape",
                headers=headers,
                json=data,
                timeout=60,
            )
            return resp.json()
        except Exception as e:
            logger.error(f"BrowserBase scrape error: {e}")
            return {"error": str(e)}
    
    def screenshot(self, url: str) -> Dict[str, Any]:
        """Take screenshot."""
        if not url:
            return {"error": "url is required"}
        if not self.api_key:
            return {"error": "BROWSERBASE_API_KEY required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {"url": url, "projectId": self.project_id}
            resp = requests.post(
                "https://api.browserbase.com/v1/screenshot",
                headers=headers,
                json=data,
                timeout=60,
            )
            return resp.json()
        except Exception as e:
            logger.error(f"BrowserBase screenshot error: {e}")
            return {"error": str(e)}


def browserbase_scrape(url: str) -> Dict[str, Any]:
    """Scrape with BrowserBase."""
    return BrowserBaseTool().scrape(url=url)
