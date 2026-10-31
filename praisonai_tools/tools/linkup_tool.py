"""LinkUp Tool for PraisonAI Agents.

Search the web and fetch pages using LinkUp API.

Usage:
    from praisonai_tools import LinkUpTool
    
    linkup = LinkUpTool()
    results = linkup.search("AI news")
    page = linkup.fetch("https://example.com")

Environment Variables:
    LINKUP_API_KEY: LinkUp API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class LinkUpTool(BaseTool):
    """Tool for LinkUp search."""
    
    name = "linkup"
    description = "Search the web and fetch web pages as markdown using LinkUp API."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LINKUP_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        url: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        if action == "search":
            return self.search(query=query, **kwargs)
        elif action == "fetch":
            return self.fetch(url=url, **kwargs)
        return {"error": f"Unknown action: {action}"}
    
    def search(self, query: str, depth: str = "standard", output_type: str = "searchResults") -> List[Dict[str, Any]]:
        """Search LinkUp."""
        if not query:
            return [{"error": "query is required"}]
        if not self.api_key:
            return [{"error": "LINKUP_API_KEY required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {"q": query, "depth": depth, "outputType": output_type}
            resp = requests.post(
                "https://api.linkup.so/v1/search",
                headers=headers,
                json=data,
                timeout=30,
            )
            result = resp.json()
            
            if output_type == "searchResults":
                return result.get("results", [])
            return [{"content": result.get("answer", "")}]
        except Exception as e:
            logger.error(f"LinkUp search error: {e}")
            return [{"error": str(e)}]
    
    def fetch(
        self,
        url: str,
        render_js: bool = False,
        include_raw_html: bool = False,
        extract_images: bool = False,
    ) -> Dict[str, Any]:
        """Fetch a web page as markdown."""
        if not url:
            return {"error": "url is required"}
        if not self.api_key:
            return {"error": "LINKUP_API_KEY required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {"url": url, "renderJs": render_js}
            if include_raw_html:
                data["includeRawHtml"] = True
            if extract_images:
                data["extractImages"] = True
            resp = requests.post(
                "https://api.linkup.so/v1/fetch",
                headers=headers,
                json=data,
                timeout=60,
            )
            if resp.status_code >= 400:
                return {
                    "error": f"LinkUp fetch failed with HTTP {resp.status_code}",
                    "status_code": resp.status_code,
                }
            result = resp.json()
            
            page = {"url": url, "markdown": result.get("markdown", "")}
            if include_raw_html:
                page["raw_html"] = result.get("rawHtml", "")
            if extract_images:
                page["images"] = result.get("images", [])
            return page
        except Exception as e:
            logger.error(f"LinkUp fetch error: {e}")
            return {"error": str(e)}


def linkup_search(query: str) -> List[Dict[str, Any]]:
    """Search with LinkUp."""
    return LinkUpTool().search(query=query)


def linkup_fetch(url: str, render_js: bool = False) -> Dict[str, Any]:
    """Fetch a web page as markdown using LinkUp.
    
    Args:
        url: URL of the page to fetch
        render_js: Render JavaScript before extracting content (slower)
        
    Returns:
        Dict with url and markdown keys
    """
    return LinkUpTool().fetch(url=url, render_js=render_js)
