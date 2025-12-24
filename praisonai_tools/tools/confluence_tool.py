"""Confluence Tool for PraisonAI Agents.

Manage Confluence pages and spaces.

Usage:
    from praisonai_tools import ConfluenceTool
    
    confluence = ConfluenceTool()
    pages = confluence.search("project docs")

Environment Variables:
    CONFLUENCE_URL: Confluence URL
    CONFLUENCE_USERNAME: Username
    CONFLUENCE_API_TOKEN: API token
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ConfluenceTool(BaseTool):
    """Tool for Confluence wiki."""
    
    name = "confluence"
    description = "Manage Confluence pages and spaces."
    
    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        self.url = url or os.getenv("CONFLUENCE_URL")
        self.username = username or os.getenv("CONFLUENCE_USERNAME")
        self.api_token = api_token or os.getenv("CONFLUENCE_API_TOKEN")
        super().__init__()
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        if not all([self.url, self.username, self.api_token]):
            return {"error": "CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN required"}
        
        url = f"{self.url}/wiki/rest/api/{endpoint}"
        auth = (self.username, self.api_token)
        headers = {"Content-Type": "application/json"}
        
        try:
            if method == "GET":
                resp = requests.get(url, auth=auth, headers=headers, timeout=10)
            elif method == "POST":
                resp = requests.post(url, auth=auth, headers=headers, json=data, timeout=10)
            else:
                return {"error": f"Unknown method: {method}"}
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(query=query)
        elif action == "get_page":
            return self.get_page(page_id=kwargs.get("page_id"))
        elif action == "create_page":
            return self.create_page(**kwargs)
        elif action == "list_spaces":
            return self.list_spaces()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search Confluence."""
        if not query:
            return [{"error": "query is required"}]
        result = self._request("GET", f"content/search?cql=text~\"{query}\"")
        if "error" in result:
            return [result]
        return result.get("results", [])
    
    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get page by ID."""
        if not page_id:
            return {"error": "page_id is required"}
        return self._request("GET", f"content/{page_id}?expand=body.storage")
    
    def create_page(self, space_key: str, title: str, content: str) -> Dict[str, Any]:
        """Create a page."""
        if not space_key or not title or not content:
            return {"error": "space_key, title, and content are required"}
        data = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {"storage": {"value": content, "representation": "storage"}},
        }
        return self._request("POST", "content", data)
    
    def list_spaces(self) -> List[Dict[str, Any]]:
        """List spaces."""
        result = self._request("GET", "space")
        if "error" in result:
            return [result]
        return result.get("results", [])


def confluence_search(query: str) -> List[Dict[str, Any]]:
    """Search Confluence."""
    return ConfluenceTool().search(query=query)
