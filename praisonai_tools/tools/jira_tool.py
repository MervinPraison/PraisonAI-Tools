"""Jira Tool for PraisonAI Agents.

Manage Jira issues, projects, and Kanban boards.

Usage:
    from praisonai_tools import JiraTool
    
    jira = JiraTool()
    issues = jira.search("project = PROJ AND status = Open")
    
    # Kanban operations
    boards = jira.list_boards()
    issues = jira.get_board_issues(board_id=2)
    jira.move_issue(issue_key="KAN-1", status="In Progress")

Environment Variables:
    JIRA_URL: Jira instance URL
    JIRA_EMAIL: Jira user email
    JIRA_API_TOKEN: Jira API token
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class JiraTool(BaseTool):
    """Tool for managing Jira issues and Kanban boards."""
    
    name = "jira"
    description = "Create, search, and manage Jira issues. Manage Kanban boards and transitions."
    
    def __init__(
        self,
        url: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        self.url = url or os.getenv("JIRA_URL")
        self.email = email or os.getenv("JIRA_EMAIL")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN")
        self._client = None
        self._session = None
        super().__init__()
    
    @property
    def session(self):
        """Get requests session for Agile API calls."""
        if self._session is None:
            try:
                import requests
                from requests.auth import HTTPBasicAuth
            except ImportError:
                raise ImportError("requests not installed. Install with: pip install requests")
            
            self._session = requests.Session()
            # Use HTTPBasicAuth for Jira Cloud API
            self._session.auth = HTTPBasicAuth(self.email, self.api_token)
            self._session.headers.update({
                "Accept": "application/json",
                "Content-Type": "application/json"
            })
        return self._session
    
    def _agile_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make a request to the Jira Agile REST API."""
        if not all([self.url, self.email, self.api_token]):
            return {"error": "JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN required"}
        
        url = f"{self.url.rstrip('/')}/rest/agile/1.0{endpoint}"
        
        try:
            if method == "GET":
                response = self.session.get(url, params=params)
            elif method == "POST":
                response = self.session.post(url, json=data, params=params)
            elif method == "PUT":
                response = self.session.put(url, json=data, params=params)
            else:
                return {"error": f"Unsupported method: {method}"}
            
            response.raise_for_status()
            return response.json() if response.text else {"success": True}
        except Exception as e:
            logger.error(f"Jira Agile API error: {e}")
            return {"error": str(e)}
    
    @property
    def client(self):
        if self._client is None:
            try:
                from jira import JIRA
            except ImportError:
                raise ImportError("jira not installed. Install with: pip install jira")
            
            if not all([self.url, self.email, self.api_token]):
                raise ValueError("JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN required")
            
            self._client = JIRA(
                server=self.url,
                basic_auth=(self.email, self.api_token),
            )
        return self._client
    
    def run(
        self,
        action: str = "search",
        jql: Optional[str] = None,
        issue_key: Optional[str] = None,
        project: Optional[str] = None,
        summary: Optional[str] = None,
        board_id: Optional[int] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(jql=jql)
        elif action == "get_issue":
            return self.get_issue(issue_key=issue_key)
        elif action == "create_issue":
            return self.create_issue(project=project, summary=summary, **kwargs)
        elif action == "update_issue":
            return self.update_issue(issue_key=issue_key, **kwargs)
        elif action == "add_comment":
            return self.add_comment(issue_key=issue_key, comment=kwargs.get("comment"))
        elif action == "list_projects":
            return self.list_projects()
        # Kanban/Board actions
        elif action == "list_boards":
            return self.list_boards(board_type=kwargs.get("board_type"))
        elif action == "get_board":
            return self.get_board(board_id=board_id)
        elif action == "get_board_configuration":
            return self.get_board_configuration(board_id=board_id)
        elif action == "get_board_issues":
            return self.get_board_issues(board_id=board_id, jql=jql)
        elif action == "get_backlog":
            return self.get_backlog(board_id=board_id)
        elif action == "get_transitions":
            return self.get_transitions(issue_key=issue_key)
        elif action == "transition_issue":
            return self.transition_issue(
                issue_key=issue_key,
                transition_id=kwargs.get("transition_id"),
                transition_name=kwargs.get("transition_name"),
                comment=kwargs.get("comment")
            )
        elif action == "move_issue":
            return self.move_issue(issue_key=issue_key, status=kwargs.get("status"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search issues with JQL."""
        if not jql:
            return [{"error": "jql is required"}]
        
        try:
            issues = self.client.search_issues(jql, maxResults=max_results)
            return [
                {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": str(issue.fields.status),
                    "assignee": str(issue.fields.assignee) if issue.fields.assignee else None,
                    "priority": str(issue.fields.priority) if issue.fields.priority else None,
                    "created": str(issue.fields.created),
                }
                for issue in issues
            ]
        except Exception as e:
            logger.error(f"Jira search error: {e}")
            return [{"error": str(e)}]
    
    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get issue details."""
        if not issue_key:
            return {"error": "issue_key is required"}
        
        try:
            issue = self.client.issue(issue_key)
            return {
                "key": issue.key,
                "summary": issue.fields.summary,
                "description": issue.fields.description,
                "status": str(issue.fields.status),
                "assignee": str(issue.fields.assignee) if issue.fields.assignee else None,
                "reporter": str(issue.fields.reporter) if issue.fields.reporter else None,
                "priority": str(issue.fields.priority) if issue.fields.priority else None,
                "created": str(issue.fields.created),
                "updated": str(issue.fields.updated),
            }
        except Exception as e:
            logger.error(f"Jira get_issue error: {e}")
            return {"error": str(e)}
    
    def create_issue(
        self,
        project: str,
        summary: str,
        description: Optional[str] = None,
        issue_type: str = "Task",
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new issue."""
        if not project or not summary:
            return {"error": "project and summary are required"}
        
        try:
            fields = {
                "project": {"key": project},
                "summary": summary,
                "issuetype": {"name": issue_type},
            }
            
            if description:
                fields["description"] = description
            if priority:
                fields["priority"] = {"name": priority}
            if assignee:
                fields["assignee"] = {"name": assignee}
            
            issue = self.client.create_issue(fields=fields)
            return {
                "success": True,
                "key": issue.key,
                "url": f"{self.url}/browse/{issue.key}",
            }
        except Exception as e:
            logger.error(f"Jira create_issue error: {e}")
            return {"error": str(e)}
    
    def update_issue(self, issue_key: str, **fields) -> Dict[str, Any]:
        """Update an issue."""
        if not issue_key:
            return {"error": "issue_key is required"}
        
        try:
            issue = self.client.issue(issue_key)
            update_fields = {}
            
            if "summary" in fields:
                update_fields["summary"] = fields["summary"]
            if "description" in fields:
                update_fields["description"] = fields["description"]
            if "status" in fields:
                self.client.transition_issue(issue, fields["status"])
            
            if update_fields:
                issue.update(fields=update_fields)
            
            return {"success": True, "key": issue_key}
        except Exception as e:
            logger.error(f"Jira update_issue error: {e}")
            return {"error": str(e)}
    
    def add_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        """Add comment to issue."""
        if not issue_key or not comment:
            return {"error": "issue_key and comment are required"}
        
        try:
            self.client.add_comment(issue_key, comment)
            return {"success": True, "key": issue_key}
        except Exception as e:
            logger.error(f"Jira add_comment error: {e}")
            return {"error": str(e)}
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects."""
        try:
            projects = self.client.projects()
            return [
                {"key": p.key, "name": p.name}
                for p in projects
            ]
        except Exception as e:
            logger.error(f"Jira list_projects error: {e}")
            return [{"error": str(e)}]
    
    # ==================== Kanban/Board Operations ====================
    
    def list_boards(
        self,
        board_type: Optional[str] = None,
        project_key: Optional[str] = None,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """List all boards.
        
        Args:
            board_type: Filter by board type ('kanban' or 'scrum')
            project_key: Filter by project key
            max_results: Maximum number of boards to return
        
        Returns:
            List of board dictionaries with id, name, type
        """
        try:
            # Use jira library's boards method if available
            boards = self.client.boards(maxResults=max_results, type=board_type, projectKeyOrID=project_key)
            return [
                {
                    "id": b.id,
                    "name": b.name,
                    "type": b.type if hasattr(b, 'type') else None,
                    "location": b.location.projectKey if hasattr(b, 'location') and hasattr(b.location, 'projectKey') else None
                }
                for b in boards
            ]
        except AttributeError:
            # Fallback to REST API if boards() not available
            params = {"maxResults": max_results}
            if board_type:
                params["type"] = board_type
            if project_key:
                params["projectKeyOrId"] = project_key
            
            result = self._agile_request("/board", params=params)
            
            if "error" in result:
                return [result]
            
            boards = result.get("values", [])
            return [
                {
                    "id": b.get("id"),
                    "name": b.get("name"),
                    "type": b.get("type"),
                    "location": b.get("location", {}).get("projectKey")
                }
                for b in boards
            ]
        except Exception as e:
            logger.error(f"Jira list_boards error: {e}")
            return [{"error": str(e)}]
    
    def get_board(self, board_id: int) -> Dict[str, Any]:
        """Get a specific board by ID.
        
        Args:
            board_id: The board ID
        
        Returns:
            Board details dictionary
        """
        if not board_id:
            return {"error": "board_id is required"}
        
        result = self._agile_request(f"/board/{board_id}")
        
        if "error" in result:
            return result
        
        return {
            "id": result.get("id"),
            "name": result.get("name"),
            "type": result.get("type"),
            "location": result.get("location", {})
        }
    
    def get_board_configuration(self, board_id: int) -> Dict[str, Any]:
        """Get board configuration including columns.
        
        Args:
            board_id: The board ID
        
        Returns:
            Board configuration with columns
        """
        if not board_id:
            return {"error": "board_id is required"}
        
        result = self._agile_request(f"/board/{board_id}/configuration")
        
        if "error" in result:
            return result
        
        column_config = result.get("columnConfig", {})
        columns = column_config.get("columns", [])
        
        return {
            "columns": [
                {
                    "name": c.get("name"),
                    "statuses": [s.get("id") for s in c.get("statuses", [])]
                }
                for c in columns
            ]
        }
    
    def get_board_issues(
        self,
        board_id: int,
        jql: Optional[str] = None,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Get issues on a board.
        
        Args:
            board_id: The board ID
            jql: Optional JQL filter
            max_results: Maximum number of issues
        
        Returns:
            List of issues on the board
        """
        if not board_id:
            return [{"error": "board_id is required"}]
        
        params = {"maxResults": max_results}
        if jql:
            params["jql"] = jql
        
        result = self._agile_request(f"/board/{board_id}/issue", params=params)
        
        if "error" in result:
            return [result]
        
        issues = result.get("issues", [])
        return [
            {
                "key": i.get("key"),
                "summary": i.get("fields", {}).get("summary"),
                "status": i.get("fields", {}).get("status", {}).get("name"),
                "assignee": i.get("fields", {}).get("assignee", {}).get("displayName") if i.get("fields", {}).get("assignee") else None,
            }
            for i in issues
        ]
    
    def get_backlog(self, board_id: int, max_results: int = 50) -> List[Dict[str, Any]]:
        """Get backlog issues for a board.
        
        Args:
            board_id: The board ID
            max_results: Maximum number of issues
        
        Returns:
            List of backlog issues
        """
        if not board_id:
            return [{"error": "board_id is required"}]
        
        params = {"maxResults": max_results}
        result = self._agile_request(f"/board/{board_id}/backlog", params=params)
        
        if "error" in result:
            return [result]
        
        issues = result.get("issues", [])
        return [
            {
                "key": i.get("key"),
                "summary": i.get("fields", {}).get("summary"),
                "status": i.get("fields", {}).get("status", {}).get("name"),
            }
            for i in issues
        ]
    
    # ==================== Transition Operations ====================
    
    def get_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get available transitions for an issue.
        
        Args:
            issue_key: The issue key (e.g., 'KAN-1')
        
        Returns:
            List of available transitions
        """
        if not issue_key:
            return [{"error": "issue_key is required"}]
        
        try:
            transitions = self.client.transitions(issue_key)
            return [
                {
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "to": t.get("to", {}).get("name")
                }
                for t in transitions
            ]
        except Exception as e:
            logger.error(f"Jira get_transitions error: {e}")
            return [{"error": str(e)}]
    
    def transition_issue(
        self,
        issue_key: str,
        transition_id: Optional[str] = None,
        transition_name: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transition an issue to a new status.
        
        Args:
            issue_key: The issue key (e.g., 'KAN-1')
            transition_id: The transition ID (use this OR transition_name)
            transition_name: The transition name (use this OR transition_id)
            comment: Optional comment to add during transition
        
        Returns:
            Success/error dictionary
        """
        if not issue_key:
            return {"error": "issue_key is required"}
        
        if not transition_id and not transition_name:
            return {"error": "transition_id or transition_name is required"}
        
        try:
            # If transition_name provided, find the ID
            if transition_name and not transition_id:
                transitions = self.client.transitions(issue_key)
                for t in transitions:
                    if t.get("name", "").lower() == transition_name.lower():
                        transition_id = t.get("id")
                        break
                
                if not transition_id:
                    available = [t.get("name") for t in transitions]
                    return {
                        "error": f"Transition '{transition_name}' not found. Available: {available}"
                    }
            
            # Perform the transition
            fields = {}
            if comment:
                self.client.add_comment(issue_key, comment)
            
            self.client.transition_issue(issue_key, transition_id, fields=fields)
            
            return {"success": True, "key": issue_key, "transition_id": transition_id}
        except Exception as e:
            logger.error(f"Jira transition_issue error: {e}")
            return {"error": str(e)}
    
    def move_issue(self, issue_key: str, status: str) -> Dict[str, Any]:
        """Move an issue to a specific status (convenience method).
        
        This is a user-friendly wrapper around transition_issue that
        finds the right transition to reach the desired status.
        
        Args:
            issue_key: The issue key (e.g., 'KAN-1')
            status: The target status name (e.g., 'In Progress', 'Done')
        
        Returns:
            Success/error dictionary
        """
        if not issue_key:
            return {"error": "issue_key is required"}
        if not status:
            return {"error": "status is required"}
        
        try:
            # Get available transitions
            transitions = self.client.transitions(issue_key)
            
            # Find transition that leads to the desired status
            transition_id = None
            for t in transitions:
                to_status = t.get("to", {}).get("name", "")
                if to_status.lower() == status.lower():
                    transition_id = t.get("id")
                    break
                # Also check transition name
                if t.get("name", "").lower() == status.lower():
                    transition_id = t.get("id")
                    break
            
            if not transition_id:
                available = [t.get("to", {}).get("name") for t in transitions]
                return {
                    "error": f"Cannot move to status '{status}'. Available: {available}"
                }
            
            self.client.transition_issue(issue_key, transition_id)
            return {"success": True, "key": issue_key, "status": status}
        except Exception as e:
            logger.error(f"Jira move_issue error: {e}")
            return {"error": str(e)}


# ==================== Standalone Tool Functions ====================

def jira_search(jql: str) -> List[Dict[str, Any]]:
    """Search Jira issues."""
    return JiraTool().search(jql=jql)


def jira_list_boards(board_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all Jira boards.
    
    Args:
        board_type: Optional filter ('kanban' or 'scrum')
    
    Returns:
        List of boards
    """
    return JiraTool().list_boards(board_type=board_type)


def jira_get_board(board_id: int) -> Dict[str, Any]:
    """Get a specific Jira board.
    
    Args:
        board_id: The board ID
    
    Returns:
        Board details
    """
    return JiraTool().get_board(board_id=board_id)


def jira_get_board_issues(board_id: int, jql: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get issues on a Jira board.
    
    Args:
        board_id: The board ID
        jql: Optional JQL filter
    
    Returns:
        List of issues
    """
    return JiraTool().get_board_issues(board_id=board_id, jql=jql)


def jira_get_backlog(board_id: int) -> List[Dict[str, Any]]:
    """Get backlog issues for a board.
    
    Args:
        board_id: The board ID
    
    Returns:
        List of backlog issues
    """
    return JiraTool().get_backlog(board_id=board_id)


def jira_get_transitions(issue_key: str) -> List[Dict[str, Any]]:
    """Get available transitions for an issue.
    
    Args:
        issue_key: The issue key (e.g., 'KAN-1')
    
    Returns:
        List of available transitions
    """
    return JiraTool().get_transitions(issue_key=issue_key)


def jira_move_issue(issue_key: str, status: str) -> Dict[str, Any]:
    """Move an issue to a specific status.
    
    Args:
        issue_key: The issue key (e.g., 'KAN-1')
        status: The target status (e.g., 'In Progress', 'Done')
    
    Returns:
        Success/error dictionary
    """
    return JiraTool().move_issue(issue_key=issue_key, status=status)


def jira_create_task(
    project: str,
    summary: str,
    description: Optional[str] = None,
    issue_type: str = "Task",
    priority: Optional[str] = None,
    assignee: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new Jira task.
    
    Args:
        project: Project key (e.g., 'KAN')
        summary: Task summary/title
        description: Optional description
        issue_type: Issue type (default: 'Task')
        priority: Optional priority
        assignee: Optional assignee
    
    Returns:
        Created issue details
    """
    return JiraTool().create_issue(
        project=project,
        summary=summary,
        description=description,
        issue_type=issue_type,
        priority=priority,
        assignee=assignee
    )
