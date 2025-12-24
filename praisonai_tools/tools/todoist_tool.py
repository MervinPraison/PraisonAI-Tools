"""Todoist Tool for PraisonAI Agents.

Manage Todoist tasks and projects.

Usage:
    from praisonai_tools import TodoistTool
    
    todoist = TodoistTool()
    tasks = todoist.list_tasks()

Environment Variables:
    TODOIST_API_TOKEN: Todoist API token
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class TodoistTool(BaseTool):
    """Tool for Todoist task management."""
    
    name = "todoist"
    description = "Manage Todoist tasks and projects."
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("TODOIST_API_TOKEN")
        self._api = None
        super().__init__()
    
    @property
    def api(self):
        if self._api is None:
            try:
                from todoist_api_python.api import TodoistAPI
            except ImportError:
                raise ImportError("todoist-api-python not installed")
            if not self.api_token:
                raise ValueError("TODOIST_API_TOKEN required")
            self._api = TodoistAPI(self.api_token)
        return self._api
    
    def run(
        self,
        action: str = "list_tasks",
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list_tasks":
            return self.list_tasks(**kwargs)
        elif action == "create_task":
            return self.create_task(**kwargs)
        elif action == "complete_task":
            return self.complete_task(task_id=kwargs.get("task_id"))
        elif action == "list_projects":
            return self.list_projects()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_tasks(self, project_id: str = None) -> List[Dict[str, Any]]:
        """List tasks."""
        try:
            if project_id:
                tasks = self.api.get_tasks(project_id=project_id)
            else:
                tasks = self.api.get_tasks()
            return [{"id": t.id, "content": t.content, "due": t.due.string if t.due else None} for t in tasks]
        except Exception as e:
            logger.error(f"Todoist list_tasks error: {e}")
            return [{"error": str(e)}]
    
    def create_task(self, content: str, project_id: str = None, due_string: str = None) -> Dict[str, Any]:
        """Create a task."""
        if not content:
            return {"error": "content is required"}
        try:
            kwargs = {"content": content}
            if project_id:
                kwargs["project_id"] = project_id
            if due_string:
                kwargs["due_string"] = due_string
            task = self.api.add_task(**kwargs)
            return {"id": task.id, "content": task.content}
        except Exception as e:
            logger.error(f"Todoist create_task error: {e}")
            return {"error": str(e)}
    
    def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Complete a task."""
        if not task_id:
            return {"error": "task_id is required"}
        try:
            self.api.close_task(task_id)
            return {"success": True}
        except Exception as e:
            logger.error(f"Todoist complete_task error: {e}")
            return {"error": str(e)}
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """List projects."""
        try:
            projects = self.api.get_projects()
            return [{"id": p.id, "name": p.name} for p in projects]
        except Exception as e:
            logger.error(f"Todoist list_projects error: {e}")
            return [{"error": str(e)}]


def todoist_list_tasks() -> List[Dict[str, Any]]:
    """List Todoist tasks."""
    return TodoistTool().list_tasks()
