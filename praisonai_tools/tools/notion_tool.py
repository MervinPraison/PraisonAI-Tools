"""Notion Tool for PraisonAI Agents.

Interact with Notion workspaces - create pages, query databases, update content.

Usage:
    from praisonai_tools import NotionTool
    
    notion = NotionTool()  # Uses NOTION_API_KEY env var
    
    # Search pages
    results = notion.search("meeting notes")
    
    # Create a page
    notion.create_page(parent_id="...", title="New Page", content="Hello!")

Environment Variables:
    NOTION_API_KEY: Notion Integration Token (Internal Integration)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class NotionTool(BaseTool):
    """Tool for interacting with Notion."""
    
    name = "notion"
    description = "Interact with Notion - search, create pages, query databases."
    
    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        """Initialize NotionTool.
        
        Args:
            api_key: Notion Integration Token (or use NOTION_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
        self.api_base = "https://api.notion.com/v1"
        self.api_version = "2022-06-28"
        super().__init__()
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make Notion API request."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        if not self.api_key:
            return {"error": "NOTION_API_KEY not configured"}
        
        try:
            url = f"{self.api_base}/{endpoint}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Notion-Version": self.api_version,
            }
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data or {}, timeout=10)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data or {}, timeout=10)
            else:
                return {"error": f"Unsupported method: {method}"}
            
            result = response.json()
            
            if response.status_code >= 400:
                return {"error": result.get("message", f"HTTP {response.status_code}")}
            
            return result
        except Exception as e:
            logger.error(f"Notion API error: {e}")
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        page_id: Optional[str] = None,
        database_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        """Execute Notion action."""
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(query=query)
        elif action == "get_page":
            return self.get_page(page_id=page_id)
        elif action == "create_page":
            return self.create_page(parent_id=parent_id, title=title, content=content)
        elif action == "query_database":
            return self.query_database(database_id=database_id, **kwargs)
        elif action == "get_database":
            return self.get_database(database_id=database_id)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(self, query: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search Notion workspace.
        
        Args:
            query: Search query
            limit: Max results
            
        Returns:
            List of search results
        """
        data = {"page_size": limit}
        if query:
            data["query"] = query
        
        result = self._request("POST", "search", data)
        
        if "error" in result:
            return [result]
        
        items = []
        for item in result.get("results", []):
            obj_type = item.get("object")
            
            if obj_type == "page":
                title = ""
                props = item.get("properties", {})
                for prop in props.values():
                    if prop.get("type") == "title":
                        title_arr = prop.get("title", [])
                        if title_arr:
                            title = title_arr[0].get("plain_text", "")
                        break
                
                items.append({
                    "id": item.get("id"),
                    "type": "page",
                    "title": title,
                    "url": item.get("url"),
                    "created_time": item.get("created_time"),
                })
            elif obj_type == "database":
                title = ""
                title_arr = item.get("title", [])
                if title_arr:
                    title = title_arr[0].get("plain_text", "")
                
                items.append({
                    "id": item.get("id"),
                    "type": "database",
                    "title": title,
                    "url": item.get("url"),
                })
        
        return items
    
    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get page details.
        
        Args:
            page_id: Notion page ID
            
        Returns:
            Page details
        """
        if not page_id:
            return {"error": "page_id is required"}
        
        result = self._request("GET", f"pages/{page_id}")
        
        if "error" in result:
            return result
        
        title = ""
        props = result.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title":
                title_arr = prop.get("title", [])
                if title_arr:
                    title = title_arr[0].get("plain_text", "")
                break
        
        return {
            "id": result.get("id"),
            "title": title,
            "url": result.get("url"),
            "created_time": result.get("created_time"),
            "last_edited_time": result.get("last_edited_time"),
            "properties": props,
        }
    
    def create_page(
        self,
        parent_id: str,
        title: str,
        content: Optional[str] = None,
        parent_type: str = "page",
    ) -> Dict[str, Any]:
        """Create a new page.
        
        Args:
            parent_id: Parent page or database ID
            title: Page title
            content: Page content (plain text)
            parent_type: "page" or "database"
            
        Returns:
            Created page info
        """
        if not parent_id:
            return {"error": "parent_id is required"}
        if not title:
            return {"error": "title is required"}
        
        # Build parent reference
        if parent_type == "database":
            parent = {"database_id": parent_id}
            properties = {
                "Name": {"title": [{"text": {"content": title}}]}
            }
        else:
            parent = {"page_id": parent_id}
            properties = {
                "title": {"title": [{"text": {"content": title}}]}
            }
        
        data = {
            "parent": parent,
            "properties": properties,
        }
        
        # Add content as children blocks
        if content:
            data["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    }
                }
            ]
        
        result = self._request("POST", "pages", data)
        
        if "error" in result:
            return result
        
        return {
            "success": True,
            "id": result.get("id"),
            "url": result.get("url"),
        }
    
    def query_database(
        self,
        database_id: str,
        filter_obj: Optional[Dict] = None,
        sorts: Optional[List[Dict]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query a Notion database.
        
        Args:
            database_id: Database ID
            filter_obj: Notion filter object
            sorts: Sort configuration
            limit: Max results
            
        Returns:
            List of database entries
        """
        if not database_id:
            return [{"error": "database_id is required"}]
        
        data = {"page_size": min(limit, 100)}
        if filter_obj:
            data["filter"] = filter_obj
        if sorts:
            data["sorts"] = sorts
        
        result = self._request("POST", f"databases/{database_id}/query", data)
        
        if "error" in result:
            return [result]
        
        items = []
        for item in result.get("results", []):
            props = item.get("properties", {})
            
            # Extract property values
            extracted = {"id": item.get("id"), "url": item.get("url")}
            for name, prop in props.items():
                prop_type = prop.get("type")
                if prop_type == "title":
                    arr = prop.get("title", [])
                    extracted[name] = arr[0].get("plain_text", "") if arr else ""
                elif prop_type == "rich_text":
                    arr = prop.get("rich_text", [])
                    extracted[name] = arr[0].get("plain_text", "") if arr else ""
                elif prop_type == "number":
                    extracted[name] = prop.get("number")
                elif prop_type == "select":
                    sel = prop.get("select")
                    extracted[name] = sel.get("name") if sel else None
                elif prop_type == "multi_select":
                    extracted[name] = [s.get("name") for s in prop.get("multi_select", [])]
                elif prop_type == "checkbox":
                    extracted[name] = prop.get("checkbox")
                elif prop_type == "date":
                    date = prop.get("date")
                    extracted[name] = date.get("start") if date else None
            
            items.append(extracted)
        
        return items
    
    def get_database(self, database_id: str) -> Dict[str, Any]:
        """Get database schema/info.
        
        Args:
            database_id: Database ID
            
        Returns:
            Database info
        """
        if not database_id:
            return {"error": "database_id is required"}
        
        result = self._request("GET", f"databases/{database_id}")
        
        if "error" in result:
            return result
        
        title = ""
        title_arr = result.get("title", [])
        if title_arr:
            title = title_arr[0].get("plain_text", "")
        
        # Extract property schema
        props = {}
        for name, prop in result.get("properties", {}).items():
            props[name] = {"type": prop.get("type")}
        
        return {
            "id": result.get("id"),
            "title": title,
            "url": result.get("url"),
            "properties": props,
        }


def search_notion(query: str) -> List[Dict[str, Any]]:
    """Search Notion workspace."""
    return NotionTool().search(query=query)


def create_notion_page(parent_id: str, title: str, content: Optional[str] = None) -> Dict[str, Any]:
    """Create a Notion page."""
    return NotionTool().create_page(parent_id=parent_id, title=title, content=content)
