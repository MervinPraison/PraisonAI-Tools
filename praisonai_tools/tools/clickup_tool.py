"""ClickUp Tool for PraisonAI Agents.

Manage ClickUp tasks and spaces.

Usage:
    from praisonai_tools import ClickUpTool
    
    clickup = ClickUpTool()
    tasks = clickup.list_tasks(list_id="123")

Environment Variables:
    CLICKUP_API_KEY: ClickUp API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ClickUpTool(BaseTool):
    """Tool for ClickUp task management."""
    
    name = "clickup"
    description = "Manage ClickUp tasks and spaces."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CLICKUP_API_KEY")
        super().__init__()
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        if not self.api_key:
            return {"error": "CLICKUP_API_KEY required"}
        
        url = f"https://api.clickup.com/api/v2/{endpoint}"
        headers = {"Authorization": self.api_key}
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                resp = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PUT":
                resp = requests.put(url, headers=headers, json=data, timeout=10)
            else:
                return {"error": f"Unknown method: {method}"}
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "list_tasks",
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list_tasks":
            return self.list_tasks(list_id=kwargs.get("list_id"))
        elif action == "create_task":
            return self.create_task(**kwargs)
        elif action == "get_task":
            return self.get_task(task_id=kwargs.get("task_id"))
        elif action == "list_spaces":
            return self.list_spaces(team_id=kwargs.get("team_id"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_tasks(self, list_id: str) -> List[Dict[str, Any]]:
        """List tasks in a list."""
        if not list_id:
            return [{"error": "list_id is required"}]
        result = self._request("GET", f"list/{list_id}/task")
        if "error" in result:
            return [result]
        return result.get("tasks", [])
    
    def create_task(self, list_id: str, name: str, description: str = None) -> Dict[str, Any]:
        """Create a task."""
        if not list_id or not name:
            return {"error": "list_id and name are required"}
        data = {"name": name}
        if description:
            data["description"] = description
        return self._request("POST", f"list/{list_id}/task", data)
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task details."""
        if not task_id:
            return {"error": "task_id is required"}
        return self._request("GET", f"task/{task_id}")
    
    def list_spaces(self, team_id: str) -> List[Dict[str, Any]]:
        """List spaces in a team."""
        if not team_id:
            return [{"error": "team_id is required"}]
        result = self._request("GET", f"team/{team_id}/space")
        if "error" in result:
            return [result]
        return result.get("spaces", [])


def clickup_list_tasks(list_id: str) -> List[Dict[str, Any]]:
    """List ClickUp tasks."""
    return ClickUpTool().list_tasks(list_id=list_id)
