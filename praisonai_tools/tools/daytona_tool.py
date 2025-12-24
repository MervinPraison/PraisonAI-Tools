"""Daytona Tool for PraisonAI Agents.

Manage Daytona development environments.

Usage:
    from praisonai_tools import DaytonaTool
    
    daytona = DaytonaTool()
    workspaces = daytona.list_workspaces()

Environment Variables:
    DAYTONA_API_KEY: Daytona API key
    DAYTONA_SERVER_URL: Daytona server URL
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class DaytonaTool(BaseTool):
    """Tool for Daytona dev environments."""
    
    name = "daytona"
    description = "Manage Daytona development environments."
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        server_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("DAYTONA_API_KEY")
        self.server_url = server_url or os.getenv("DAYTONA_SERVER_URL", "https://api.daytona.io")
        super().__init__()
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        if not self.api_key:
            return {"error": "DAYTONA_API_KEY required"}
        
        url = f"{self.server_url}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                resp = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == "DELETE":
                resp = requests.delete(url, headers=headers, timeout=10)
                if resp.status_code == 204:
                    return {"success": True}
            else:
                return {"error": f"Unknown method: {method}"}
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "list_workspaces",
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list_workspaces":
            return self.list_workspaces()
        elif action == "create_workspace":
            return self.create_workspace(**kwargs)
        elif action == "delete_workspace":
            return self.delete_workspace(workspace_id=kwargs.get("workspace_id"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_workspaces(self) -> List[Dict[str, Any]]:
        """List workspaces."""
        result = self._request("GET", "workspaces")
        if isinstance(result, dict) and "error" in result:
            return [result]
        return result if isinstance(result, list) else [result]
    
    def create_workspace(self, name: str, repository: str) -> Dict[str, Any]:
        """Create workspace."""
        if not name or not repository:
            return {"error": "name and repository are required"}
        return self._request("POST", "workspaces", {"name": name, "repository": repository})
    
    def delete_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Delete workspace."""
        if not workspace_id:
            return {"error": "workspace_id is required"}
        return self._request("DELETE", f"workspaces/{workspace_id}")


def daytona_list_workspaces() -> List[Dict[str, Any]]:
    """List Daytona workspaces."""
    return DaytonaTool().list_workspaces()
