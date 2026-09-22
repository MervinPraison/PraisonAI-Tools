"""Google Tasks Tool for PraisonAI Agents.

Manage Google Tasks and task lists via the Tasks API.

Usage:
    from praisonai_tools import GoogleTasksTool

    tasks = GoogleTasksTool()
    lists = tasks.list_task_lists()
    tasks.create_task(lists[0]["id"], "Write report", due="2026-05-15T00:00:00Z")

Auth:
    Shares :class:`GoogleWorkspaceAuth` (Service Account / OAuth / ADC). Pass
    ``auth=`` to reuse a shared session across tools.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool
from praisonai_tools.tools._google_auth import GoogleWorkspaceAuth, resolve_auth

logger = logging.getLogger(__name__)


class GoogleTasksTool(BaseTool):
    """Tool for managing Google Tasks and task lists."""

    name = "google_tasks"
    description = "Create, list, complete and delete Google Tasks and task lists."

    def __init__(
        self,
        auth: Optional[GoogleWorkspaceAuth] = None,
        service_account_file: Optional[str] = None,
        credentials_file: Optional[str] = None,
        token_file: Optional[str] = None,
    ):
        self._auth = resolve_auth(
            auth,
            ["tasks"],
            service_account_file=service_account_file,
            credentials_file=credentials_file,
            token_file=token_file,
        )
        self._service = None
        super().__init__()

    @property
    def service(self):
        if self._service is None:
            self._service = self._auth.build_service("tasks", "v1", ["tasks"])
        return self._service

    def run(self, action: str = "list_tasks", **kwargs) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        actions = {
            "list_task_lists": lambda: self.list_task_lists(),
            "list_tasks": lambda: self.list_tasks(**kwargs),
            "create_task": lambda: self.create_task(**kwargs),
            "complete_task": lambda: self.complete_task(
                task_list_id=kwargs.get("task_list_id"), task_id=kwargs.get("task_id")
            ),
            "delete_task": lambda: self.delete_task(
                task_list_id=kwargs.get("task_list_id"), task_id=kwargs.get("task_id")
            ),
        }
        handler = actions.get(action)
        if handler:
            return handler()
        return {"error": f"Unknown action: {action}. Available: {', '.join(actions)}"}

    def list_task_lists(self) -> List[Dict[str, Any]]:
        """List all task lists."""
        try:
            result = self.service.tasklists().list(maxResults=100).execute()
            return [
                {"id": tl["id"], "title": tl.get("title")}
                for tl in result.get("items", [])
            ]
        except Exception as e:
            logger.error(f"Google Tasks list_task_lists error: {e}")
            return [{"error": str(e)}]

    def list_tasks(
        self, task_list_id: str, show_completed: bool = False
    ) -> List[Dict[str, Any]]:
        """List tasks in a task list."""
        if not task_list_id:
            return [{"error": "task_list_id is required"}]
        try:
            result = self.service.tasks().list(
                tasklist=task_list_id,
                showCompleted=show_completed,
                showHidden=show_completed,
                maxResults=100,
            ).execute()
            return [
                {
                    "id": t["id"],
                    "title": t.get("title"),
                    "status": t.get("status"),
                    "due": t.get("due"),
                    "notes": t.get("notes"),
                }
                for t in result.get("items", [])
            ]
        except Exception as e:
            logger.error(f"Google Tasks list_tasks error: {e}")
            return [{"error": str(e)}]

    def create_task(
        self,
        task_list_id: str,
        title: str,
        notes: Optional[str] = None,
        due: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a task. ``due`` is an RFC 3339 timestamp (e.g. 2026-05-15T00:00:00Z)."""
        if not task_list_id or not title:
            return {"error": "task_list_id and title are required"}
        try:
            body: Dict[str, Any] = {"title": title}
            if notes:
                body["notes"] = notes
            if due:
                body["due"] = due
            task = self.service.tasks().insert(tasklist=task_list_id, body=body).execute()
            return {"success": True, "id": task.get("id"), "title": task.get("title")}
        except Exception as e:
            logger.error(f"Google Tasks create_task error: {e}")
            return {"error": str(e)}

    def complete_task(self, task_list_id: str, task_id: str) -> Dict[str, Any]:
        """Mark a task as completed."""
        if not task_list_id or not task_id:
            return {"error": "task_list_id and task_id are required"}
        try:
            task = self.service.tasks().patch(
                tasklist=task_list_id, task=task_id, body={"status": "completed"}
            ).execute()
            return {"success": True, "id": task.get("id"), "status": task.get("status")}
        except Exception as e:
            logger.error(f"Google Tasks complete_task error: {e}")
            return {"error": str(e)}

    def delete_task(self, task_list_id: str, task_id: str) -> Dict[str, Any]:
        """Delete a task."""
        if not task_list_id or not task_id:
            return {"error": "task_list_id and task_id are required"}
        try:
            self.service.tasks().delete(tasklist=task_list_id, task=task_id).execute()
            return {"success": True, "deleted": task_id}
        except Exception as e:
            logger.error(f"Google Tasks delete_task error: {e}")
            return {"error": str(e)}


def list_google_task_lists() -> List[Dict[str, Any]]:
    """List Google task lists."""
    return GoogleTasksTool().list_task_lists()
