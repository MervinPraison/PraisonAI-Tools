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
            logger.error(f"Jira Agile API error: {self._mask(str(e))}")
            return {"error": self._mask(str(e))}

    def _mask(self, message: str) -> str:
        """Mask the API token in any message to avoid leaking secrets."""
        if message and self.api_token:
            return message.replace(self.api_token, "***")
        return message

    def _rest_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        version: str = "3",
    ) -> Dict[str, Any]:
        """Make a request to the Jira REST API (v2 or v3)."""
        if not all([self.url, self.email, self.api_token]):
            return {"error": "JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN required"}

        url = f"{self.url.rstrip('/')}/rest/api/{version}{endpoint}"

        try:
            if method == "GET":
                response = self.session.get(url, params=params)
            elif method == "POST":
                response = self.session.post(url, json=data, params=params)
            elif method == "PUT":
                response = self.session.put(url, json=data, params=params)
            elif method == "DELETE":
                response = self.session.delete(url, params=params)
            else:
                return {"error": f"Unsupported method: {method}"}

            response.raise_for_status()
            return response.json() if response.text else {"success": True}
        except Exception as e:
            logger.error(f"Jira REST API error: {self._mask(str(e))}")
            return {"error": self._mask(str(e))}

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
        # Sprint actions
        elif action == "list_sprints":
            return self.list_sprints(board_id=board_id, state=kwargs.get("state", "active"))
        elif action == "get_active_sprint":
            return self.get_active_sprint(board_id=board_id)
        elif action == "create_sprint":
            return self.create_sprint(
                board_id=board_id,
                name=kwargs.get("name"),
                start_date=kwargs.get("start_date"),
                end_date=kwargs.get("end_date"),
                goal=kwargs.get("goal"),
            )
        elif action == "start_sprint":
            return self.start_sprint(
                sprint_id=kwargs.get("sprint_id"),
                start_date=kwargs.get("start_date"),
                end_date=kwargs.get("end_date"),
            )
        elif action == "complete_sprint":
            return self.complete_sprint(sprint_id=kwargs.get("sprint_id"))
        elif action == "move_issues_to_sprint":
            return self.move_issues_to_sprint(
                sprint_id=kwargs.get("sprint_id"),
                issue_keys=kwargs.get("issue_keys"),
            )
        elif action == "get_sprint_issues":
            return self.get_sprint_issues(sprint_id=kwargs.get("sprint_id"), jql=jql)
        # Epic actions
        elif action == "list_epics":
            return self.list_epics(board_id=board_id, done=kwargs.get("done", False))
        elif action == "get_epic":
            return self.get_epic(epic_key=kwargs.get("epic_key"))
        elif action == "create_epic":
            return self.create_epic(
                project=project,
                name=kwargs.get("name"),
                summary=summary,
                description=kwargs.get("description"),
            )
        elif action == "get_epic_issues":
            return self.get_epic_issues(epic_key=kwargs.get("epic_key"))
        elif action == "link_issue_to_epic":
            return self.link_issue_to_epic(
                epic_key=kwargs.get("epic_key"),
                issue_keys=kwargs.get("issue_keys"),
            )
        # Bulk actions
        elif action == "bulk_create_issues":
            return self.bulk_create_issues(issues=kwargs.get("issues"))
        elif action == "bulk_transition":
            return self.bulk_transition(
                issue_keys=kwargs.get("issue_keys"),
                target_status=kwargs.get("target_status"),
            )
        # Attachment actions
        elif action == "upload_attachment":
            return self.upload_attachment(
                issue_key=issue_key,
                file_path=kwargs.get("file_path"),
                filename=kwargs.get("filename"),
            )
        elif action == "list_attachments":
            return self.list_attachments(issue_key=issue_key)
        # Worklog actions
        elif action == "log_work":
            return self.log_work(
                issue_key=issue_key,
                time_spent=kwargs.get("time_spent"),
                comment=kwargs.get("comment"),
                started=kwargs.get("started"),
            )
        elif action == "get_worklogs":
            return self.get_worklogs(issue_key=issue_key)
        # Issue links
        elif action == "link_issues":
            return self.link_issues(
                outward_issue=kwargs.get("outward_issue"),
                inward_issue=kwargs.get("inward_issue"),
                link_type=kwargs.get("link_type", "blocks"),
            )
        # Enhanced search + custom fields
        elif action == "search_all":
            return self.search_all(jql=jql, fields=kwargs.get("fields"))
        elif action == "get_custom_fields":
            return self.get_custom_fields()
        elif action == "create_issue_with_custom_fields":
            return self.create_issue_with_custom_fields(
                project=project,
                summary=summary,
                custom_fields=kwargs.get("custom_fields"),
                issue_type=kwargs.get("issue_type", "Task"),
            )
        elif action == "add_watcher":
            return self.add_watcher(
                issue_key=issue_key,
                account_id=kwargs.get("account_id"),
            )
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

    # ==================== Sprint Operations ====================

    def list_sprints(
        self, board_id: int, state: str = "active"
    ) -> List[Dict[str, Any]]:
        """List sprints on a board.

        Args:
            board_id: The board ID (must be a Scrum board)
            state: Filter by state - 'active', 'future', or 'closed'

        Returns:
            List of sprint dictionaries
        """
        if not board_id:
            return [{"error": "board_id is required"}]

        params = {}
        if state:
            params["state"] = state

        result = self._agile_request(f"/board/{board_id}/sprint", params=params)
        if "error" in result:
            return [result]

        return [
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "state": s.get("state"),
                "startDate": s.get("startDate"),
                "endDate": s.get("endDate"),
                "goal": s.get("goal"),
            }
            for s in result.get("values", [])
        ]

    def get_active_sprint(self, board_id: int) -> Dict[str, Any]:
        """Get the currently active sprint on a board.

        Args:
            board_id: The board ID

        Returns:
            Active sprint details or {"error": "no active sprint"}
        """
        sprints = self.list_sprints(board_id=board_id, state="active")
        if sprints and "error" in sprints[0]:
            return sprints[0]
        if not sprints:
            return {"error": "no active sprint"}
        return sprints[0]

    def create_sprint(
        self,
        board_id: int,
        name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        goal: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new sprint on a board.

        Args:
            board_id: The board ID
            name: Sprint name
            start_date: Optional ISO 8601 start date
            end_date: Optional ISO 8601 end date
            goal: Optional sprint goal

        Returns:
            Created sprint details
        """
        if not board_id or not name:
            return {"error": "board_id and name are required"}

        data = {"name": name, "originBoardId": board_id}
        if start_date:
            data["startDate"] = start_date
        if end_date:
            data["endDate"] = end_date
        if goal:
            data["goal"] = goal

        return self._agile_request("/sprint", method="POST", data=data)

    def start_sprint(
        self, sprint_id: int, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Transition a sprint to the active state.

        Args:
            sprint_id: The sprint ID
            start_date: ISO 8601 start date
            end_date: ISO 8601 end date

        Returns:
            Updated sprint details
        """
        if not sprint_id:
            return {"error": "sprint_id is required"}

        data = {"state": "active", "startDate": start_date, "endDate": end_date}
        return self._agile_request(
            f"/sprint/{sprint_id}", method="POST", data=data
        )

    def complete_sprint(self, sprint_id: int) -> Dict[str, Any]:
        """Mark a sprint complete.

        Args:
            sprint_id: The sprint ID

        Returns:
            Updated sprint details
        """
        if not sprint_id:
            return {"error": "sprint_id is required"}

        data = {"state": "closed"}
        return self._agile_request(
            f"/sprint/{sprint_id}", method="POST", data=data
        )

    def move_issues_to_sprint(
        self, sprint_id: int, issue_keys: List[str]
    ) -> Dict[str, Any]:
        """Move one or more issues into a sprint.

        Args:
            sprint_id: The sprint ID
            issue_keys: List of issue keys (e.g. ['PROJ-1', 'PROJ-2'])

        Returns:
            Success/error dictionary
        """
        if not sprint_id:
            return {"error": "sprint_id is required"}
        if not issue_keys:
            return {"error": "issue_keys is required"}

        data = {"issues": issue_keys}
        result = self._agile_request(
            f"/sprint/{sprint_id}/issue", method="POST", data=data
        )
        if "error" in result:
            return result
        return {"success": True, "sprint_id": sprint_id, "moved": len(issue_keys)}

    def get_sprint_issues(
        self, sprint_id: int, jql: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all issues in a sprint.

        Args:
            sprint_id: The sprint ID
            jql: Optional JQL filter

        Returns:
            List of issues in the sprint
        """
        if not sprint_id:
            return [{"error": "sprint_id is required"}]

        params = {"maxResults": 100}
        if jql:
            params["jql"] = jql

        result = self._agile_request(
            f"/sprint/{sprint_id}/issue", params=params
        )
        if "error" in result:
            return [result]

        return [
            {
                "key": i.get("key"),
                "summary": i.get("fields", {}).get("summary"),
                "status": i.get("fields", {}).get("status", {}).get("name"),
            }
            for i in result.get("issues", [])
        ]

    # ==================== Epic Operations ====================

    def list_epics(
        self, board_id: int, done: bool = False
    ) -> List[Dict[str, Any]]:
        """List all epics on a board.

        Args:
            board_id: The board ID
            done: Whether to include done epics

        Returns:
            List of epic dictionaries
        """
        if not board_id:
            return [{"error": "board_id is required"}]

        params = {"done": str(done).lower()}
        result = self._agile_request(f"/board/{board_id}/epic", params=params)
        if "error" in result:
            return [result]

        return [
            {
                "id": e.get("id"),
                "key": e.get("key"),
                "name": e.get("name"),
                "summary": e.get("summary"),
                "done": e.get("done"),
            }
            for e in result.get("values", [])
        ]

    def get_epic(self, epic_key: str) -> Dict[str, Any]:
        """Get epic details.

        Args:
            epic_key: The epic key (e.g. 'PROJ-5')

        Returns:
            Epic details
        """
        if not epic_key:
            return {"error": "epic_key is required"}
        return self._agile_request(f"/epic/{epic_key}")

    def create_epic(
        self,
        project: str,
        name: str,
        summary: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new epic.

        Args:
            project: Project key
            name: Epic name
            summary: Epic summary
            description: Optional description

        Returns:
            Created epic details
        """
        if not project or not summary:
            return {"error": "project and summary are required"}

        fields = {
            "project": {"key": project},
            "summary": summary,
            "issuetype": {"name": "Epic"},
        }
        if description:
            fields["description"] = description

        result = self._rest_request(
            "/issue", method="POST", data={"fields": fields}
        )
        if "error" in result:
            return result
        return {
            "success": True,
            "key": result.get("key"),
            "id": result.get("id"),
        }

    def get_epic_issues(self, epic_key: str) -> List[Dict[str, Any]]:
        """Get all issues belonging to an epic.

        Args:
            epic_key: The epic key

        Returns:
            List of issues in the epic
        """
        if not epic_key:
            return [{"error": "epic_key is required"}]

        result = self._agile_request(
            f"/epic/{epic_key}/issue", params={"maxResults": 100}
        )
        if "error" in result:
            return [result]

        return [
            {
                "key": i.get("key"),
                "summary": i.get("fields", {}).get("summary"),
                "status": i.get("fields", {}).get("status", {}).get("name"),
            }
            for i in result.get("issues", [])
        ]

    def link_issue_to_epic(
        self, epic_key: str, issue_keys: List[str]
    ) -> Dict[str, Any]:
        """Assign issues to an epic.

        Args:
            epic_key: The epic key
            issue_keys: List of issue keys to assign

        Returns:
            Success/error dictionary
        """
        if not epic_key:
            return {"error": "epic_key is required"}
        if not issue_keys:
            return {"error": "issue_keys is required"}

        data = {"issues": issue_keys}
        result = self._agile_request(
            f"/epic/{epic_key}/issue", method="POST", data=data
        )
        if "error" in result:
            return result
        return {"success": True, "epic": epic_key, "linked": len(issue_keys)}

    # ==================== Bulk Operations ====================

    def bulk_create_issues(
        self, issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create multiple issues, batching at Jira's 50-per-call limit.

        Args:
            issues: List of field dicts. Each dict must contain at least
                ``project``, ``summary`` and optionally ``issue_type``.

        Returns:
            List of created issue results
        """
        if not issues:
            return [{"error": "issues is required"}]

        created: List[Dict[str, Any]] = []
        for start in range(0, len(issues), 50):
            batch = issues[start : start + 50]
            payload = {"issueUpdates": []}
            for item in batch:
                fields = {
                    "project": {"key": item.get("project")},
                    "summary": item.get("summary"),
                    "issuetype": {"name": item.get("issue_type", "Task")},
                }
                if item.get("description"):
                    fields["description"] = item["description"]
                if item.get("custom_fields"):
                    fields.update(item["custom_fields"])
                payload["issueUpdates"].append({"fields": fields})

            result = self._rest_request(
                "/issue/bulk", method="POST", data=payload
            )
            if "error" in result:
                created.append(result)
                continue
            for issue in result.get("issues", []):
                created.append(
                    {"success": True, "key": issue.get("key"), "id": issue.get("id")}
                )
        return created

    def bulk_transition(
        self, issue_keys: List[str], target_status: str
    ) -> Dict[str, Any]:
        """Move multiple issues to a target status.

        Args:
            issue_keys: List of issue keys
            target_status: Target status name

        Returns:
            Summary dictionary with per-issue results
        """
        if not issue_keys:
            return {"error": "issue_keys is required"}
        if not target_status:
            return {"error": "target_status is required"}

        results = {}
        for key in issue_keys:
            res = self.move_issue(issue_key=key, status=target_status)
            results[key] = "success" if res.get("success") else res.get("error")
        succeeded = sum(1 for v in results.values() if v == "success")
        return {
            "success": succeeded == len(issue_keys),
            "transitioned": succeeded,
            "total": len(issue_keys),
            "results": results,
        }

    # ==================== Attachments ====================

    def upload_attachment(
        self,
        issue_key: str,
        file_path: str,
        filename: Optional[str] = None,
        max_size_mb: int = 10,
    ) -> Dict[str, Any]:
        """Attach a local file to an issue.

        Args:
            issue_key: The issue key
            file_path: Path to the local file
            filename: Optional override for the attachment name
            max_size_mb: Maximum allowed upload size in MB (default 10)

        Returns:
            Attachment metadata or error
        """
        if not issue_key or not file_path:
            return {"error": "issue_key and file_path are required"}
        if not os.path.exists(file_path):
            return {"error": f"file not found: {file_path}"}

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > max_size_mb:
            return {
                "error": f"file exceeds max size {max_size_mb}MB ({size_mb:.1f}MB)"
            }

        if not all([self.url, self.email, self.api_token]):
            return {"error": "JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN required"}

        url = f"{self.url.rstrip('/')}/rest/api/3/issue/{issue_key}/attachments"
        name = filename or os.path.basename(file_path)
        try:
            with open(file_path, "rb") as fh:
                response = self.session.post(
                    url,
                    files={"file": (name, fh)},
                    headers={"X-Atlassian-Token": "no-check"},
                )
            response.raise_for_status()
            data = response.json() if response.text else []
            return {
                "success": True,
                "issue": issue_key,
                "attachments": [
                    {"id": a.get("id"), "filename": a.get("filename")}
                    for a in data
                ],
            }
        except Exception as e:
            logger.error(f"Jira upload_attachment error: {self._mask(str(e))}")
            return {"error": self._mask(str(e))}

    def list_attachments(self, issue_key: str) -> List[Dict[str, Any]]:
        """List all attachments on an issue.

        Args:
            issue_key: The issue key

        Returns:
            List of attachment metadata
        """
        if not issue_key:
            return [{"error": "issue_key is required"}]

        result = self._rest_request(
            f"/issue/{issue_key}", params={"fields": "attachment"}
        )
        if "error" in result:
            return [result]

        attachments = result.get("fields", {}).get("attachment", [])
        return [
            {
                "id": a.get("id"),
                "filename": a.get("filename"),
                "size": a.get("size"),
                "created": a.get("created"),
            }
            for a in attachments
        ]

    # ==================== Worklog ====================

    def log_work(
        self,
        issue_key: str,
        time_spent: str,
        comment: Optional[str] = None,
        started: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Log work on an issue.

        Args:
            issue_key: The issue key
            time_spent: Human-readable duration (e.g. '2h 30m')
            comment: Optional worklog comment
            started: Optional ISO 8601 start timestamp

        Returns:
            Worklog details or error
        """
        if not issue_key or not time_spent:
            return {"error": "issue_key and time_spent are required"}

        data = {"timeSpent": time_spent}
        if comment:
            data["comment"] = comment
        if started:
            data["started"] = started

        result = self._rest_request(
            f"/issue/{issue_key}/worklog", method="POST", data=data
        )
        if "error" in result:
            return result
        return {
            "success": True,
            "key": issue_key,
            "worklog_id": result.get("id"),
            "timeSpent": result.get("timeSpent"),
        }

    def get_worklogs(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get all worklogs for an issue.

        Args:
            issue_key: The issue key

        Returns:
            List of worklog entries
        """
        if not issue_key:
            return [{"error": "issue_key is required"}]

        result = self._rest_request(f"/issue/{issue_key}/worklog")
        if "error" in result:
            return [result]

        return [
            {
                "id": w.get("id"),
                "author": w.get("author", {}).get("displayName"),
                "timeSpent": w.get("timeSpent"),
                "started": w.get("started"),
                "comment": w.get("comment"),
            }
            for w in result.get("worklogs", [])
        ]

    # ==================== Issue Links ====================

    def link_issues(
        self, outward_issue: str, inward_issue: str, link_type: str = "blocks"
    ) -> Dict[str, Any]:
        """Create a link between two issues.

        Args:
            outward_issue: Key of the outward issue (e.g. the blocker)
            inward_issue: Key of the inward issue (e.g. the blocked)
            link_type: Link type name (default 'blocks')

        Returns:
            Success/error dictionary
        """
        if not outward_issue or not inward_issue:
            return {"error": "outward_issue and inward_issue are required"}

        data = {
            "type": {"name": link_type},
            "outwardIssue": {"key": outward_issue},
            "inwardIssue": {"key": inward_issue},
        }
        result = self._rest_request("/issueLink", method="POST", data=data)
        if "error" in result:
            return result
        return {
            "success": True,
            "outward": outward_issue,
            "inward": inward_issue,
            "type": link_type,
        }

    # ==================== Enhanced Search (REST v3 pagination) ====================

    def search_all(
        self, jql: str, fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search with automatic nextPageToken pagination (all results).

        Args:
            jql: The JQL query
            fields: Optional list of fields to return

        Returns:
            List of all matching issues
        """
        if not jql:
            return [{"error": "jql is required"}]

        field_list = fields or ["summary", "status", "assignee"]
        issues: List[Dict[str, Any]] = []
        next_token = None
        while True:
            params = {
                "jql": jql,
                "maxResults": 100,
                "fields": ",".join(field_list),
            }
            if next_token:
                params["nextPageToken"] = next_token

            result = self._rest_request("/search/jql", params=params)
            if "error" in result:
                return [result]

            for i in result.get("issues", []):
                fields_data = i.get("fields", {})
                status = fields_data.get("status")
                assignee = fields_data.get("assignee")
                issues.append(
                    {
                        "key": i.get("key"),
                        "summary": fields_data.get("summary"),
                        "status": status.get("name") if status else None,
                        "assignee": assignee.get("displayName") if assignee else None,
                    }
                )

            next_token = result.get("nextPageToken")
            if not next_token:
                break
        return issues

    # ==================== Custom Fields ====================

    def get_custom_fields(self) -> List[Dict[str, Any]]:
        """List all custom fields in the instance.

        Returns:
            List of custom field metadata
        """
        result = self._rest_request("/field")
        if isinstance(result, dict) and "error" in result:
            return [result]

        return [
            {"id": f.get("id"), "name": f.get("name"), "type": f.get("schema", {}).get("type")}
            for f in result
            if f.get("custom")
        ]

    def create_issue_with_custom_fields(
        self,
        project: str,
        summary: str,
        custom_fields: Dict[str, Any],
        issue_type: str = "Task",
    ) -> Dict[str, Any]:
        """Create an issue with arbitrary custom field values.

        Args:
            project: Project key
            summary: Issue summary
            custom_fields: Dict of {field_id: value}
            issue_type: Issue type (default 'Task')

        Returns:
            Created issue details
        """
        if not project or not summary:
            return {"error": "project and summary are required"}

        fields = {
            "project": {"key": project},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }
        if custom_fields:
            fields.update(custom_fields)

        result = self._rest_request(
            "/issue", method="POST", data={"fields": fields}
        )
        if "error" in result:
            return result
        return {
            "success": True,
            "key": result.get("key"),
            "url": f"{self.url}/browse/{result.get('key')}",
        }

    # ==================== Watchers ====================

    def add_watcher(self, issue_key: str, account_id: str) -> Dict[str, Any]:
        """Add a watcher to an issue.

        Args:
            issue_key: The issue key
            account_id: The account ID of the watcher

        Returns:
            Success/error dictionary
        """
        if not issue_key or not account_id:
            return {"error": "issue_key and account_id are required"}

        result = self._rest_request(
            f"/issue/{issue_key}/watchers", method="POST", data=account_id
        )
        if "error" in result:
            return result
        return {"success": True, "key": issue_key, "watcher": account_id}


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


def jira_list_sprints(board_id: int, state: str = "active") -> List[Dict[str, Any]]:
    """List sprints on a board.

    Args:
        board_id: The board ID
        state: 'active', 'future', or 'closed'

    Returns:
        List of sprints
    """
    return JiraTool().list_sprints(board_id=board_id, state=state)


def jira_get_active_sprint(board_id: int) -> Dict[str, Any]:
    """Get the active sprint on a board.

    Args:
        board_id: The board ID

    Returns:
        Active sprint details
    """
    return JiraTool().get_active_sprint(board_id=board_id)


def jira_move_issues_to_sprint(sprint_id: int, issue_keys: List[str]) -> Dict[str, Any]:
    """Move issues into a sprint.

    Args:
        sprint_id: The sprint ID
        issue_keys: List of issue keys

    Returns:
        Success/error dictionary
    """
    return JiraTool().move_issues_to_sprint(sprint_id=sprint_id, issue_keys=issue_keys)


def jira_get_epic_issues(epic_key: str) -> List[Dict[str, Any]]:
    """Get all issues in an epic.

    Args:
        epic_key: The epic key

    Returns:
        List of issues
    """
    return JiraTool().get_epic_issues(epic_key=epic_key)


def jira_log_work(
    issue_key: str,
    time_spent: str,
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    """Log work on an issue.

    Args:
        issue_key: The issue key
        time_spent: Human-readable duration (e.g. '2h 30m')
        comment: Optional worklog comment

    Returns:
        Worklog details
    """
    return JiraTool().log_work(issue_key=issue_key, time_spent=time_spent, comment=comment)


def jira_search_all(jql: str) -> List[Dict[str, Any]]:
    """Search Jira issues with automatic pagination (all results).

    Args:
        jql: The JQL query

    Returns:
        List of all matching issues
    """
    return JiraTool().search_all(jql=jql)
