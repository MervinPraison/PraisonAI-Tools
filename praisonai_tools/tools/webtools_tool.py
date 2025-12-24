"""WebTools Tool for PraisonAI Agents.

Common web utilities like URL parsing, HTTP requests.

Usage:
    from praisonai_tools import WebToolsTool
    
    web = WebToolsTool()
    response = web.fetch("https://api.example.com/data")
"""

import logging
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse, parse_qs

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class WebToolsTool(BaseTool):
    """Tool for common web utilities."""
    
    name = "webtools"
    description = "Common web utilities like URL parsing, HTTP requests."
    
    def run(
        self,
        action: str = "fetch",
        url: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        action = action.lower().replace("-", "_")
        
        if action == "fetch":
            return self.fetch(url=url, **kwargs)
        elif action == "parse_url":
            return self.parse_url(url=url)
        elif action == "head":
            return self.head(url=url)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def fetch(self, url: str, method: str = "GET", headers: Dict = None, data: Dict = None) -> Dict[str, Any]:
        """Fetch URL content."""
        if not url:
            return {"error": "url is required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            if method.upper() == "GET":
                resp = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                resp = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                return {"error": f"Unsupported method: {method}"}
            
            return {
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "content": resp.text[:10000],
            }
        except Exception as e:
            logger.error(f"WebTools fetch error: {e}")
            return {"error": str(e)}
    
    def parse_url(self, url: str) -> Dict[str, Any]:
        """Parse URL components."""
        if not url:
            return {"error": "url is required"}
        
        try:
            parsed = urlparse(url)
            return {
                "scheme": parsed.scheme,
                "netloc": parsed.netloc,
                "path": parsed.path,
                "params": parsed.params,
                "query": parse_qs(parsed.query),
                "fragment": parsed.fragment,
            }
        except Exception as e:
            logger.error(f"WebTools parse_url error: {e}")
            return {"error": str(e)}
    
    def head(self, url: str) -> Dict[str, Any]:
        """Get URL headers only."""
        if not url:
            return {"error": "url is required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            return {
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "url": resp.url,
            }
        except Exception as e:
            logger.error(f"WebTools head error: {e}")
            return {"error": str(e)}


def webtools_fetch(url: str) -> Dict[str, Any]:
    """Fetch URL."""
    return WebToolsTool().fetch(url=url)
