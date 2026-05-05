"""Linear Tool for PraisonAI Agents.

Manage Linear issues and projects.

Usage:
    from praisonai_tools import LinearTool
    
    linear = LinearTool()
    issues = linear.list_issues()

Environment Variables:
    LINEAR_API_KEY: Linear personal API key (sent as raw Authorization header)
    LINEAR_OAUTH_TOKEN: Linear OAuth access token (sent with 'Bearer ' prefix)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class LinearTool(BaseTool):
    """Tool for managing Linear issues."""
    
    name = "linear"
    description = "Create and manage Linear issues and projects."
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        oauth_token: Optional[str] = None,
    ):
        # Personal API key takes precedence over OAuth when both are provided
        self.api_key = api_key or os.getenv("LINEAR_API_KEY")
        self.oauth_token = oauth_token or os.getenv("LINEAR_OAUTH_TOKEN")
        self.api_url = "https://api.linear.app/graphql"
        super().__init__()

    def _auth_header(self) -> Optional[str]:
        """Return Authorization header value, or None if no credentials configured.

        Personal API keys are sent raw; OAuth tokens require the 'Bearer ' prefix.
        """
        if self.api_key:
            return self.api_key
        if self.oauth_token:
            return f"Bearer {self.oauth_token}"
        return None

    def _graphql(self, query: str, variables: Dict = None) -> Dict:
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        auth = self._auth_header()
        if not auth:
            return {"error": "LINEAR_API_KEY or LINEAR_OAUTH_TOKEN required"}

        try:
            resp = requests.post(
                self.api_url,
                headers={"Authorization": auth, "Content-Type": "application/json"},
                json={"query": query, "variables": variables or {}},
                timeout=10,
            )
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "list_issues",
        issue_id: Optional[str] = None,
        title: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list_issues":
            return self.list_issues(**kwargs)
        elif action == "get_issue":
            return self.get_issue(issue_id=issue_id)
        elif action == "create_issue":
            return self.create_issue(title=title, **kwargs)
        elif action == "update_issue":
            if title is not None:
                kwargs.setdefault("title", title)
            return self.update_issue(issue_id=issue_id, **kwargs)
        elif action == "add_comment":
            return self.add_comment(issue_id=issue_id, **kwargs)
        elif action == "list_teams":
            return self.list_teams()
        elif action == "list_cycles":
            return self.list_cycles(**kwargs)
        elif action == "list_issue_states":
            return self.list_issue_states(**kwargs)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_issues(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List issues."""
        query = """
        query($first: Int) {
            issues(first: $first) {
                nodes {
                    id
                    title
                    state { name }
                    priority
                    assignee { name }
                    createdAt
                }
            }
        }
        """
        result = self._graphql(query, {"first": limit})
        if "error" in result:
            return [result]
        
        issues = result.get("data", {}).get("issues", {}).get("nodes", [])
        return [
            {
                "id": i["id"],
                "title": i["title"],
                "state": i.get("state", {}).get("name"),
                "priority": i.get("priority"),
                "assignee": i.get("assignee", {}).get("name") if i.get("assignee") else None,
            }
            for i in issues
        ]
    
    def get_issue(self, issue_id: str) -> Dict[str, Any]:
        """Get issue details."""
        if not issue_id:
            return {"error": "issue_id required"}
        
        query = """
        query($id: String!) {
            issue(id: $id) {
                id
                title
                description
                state { name }
                priority
                assignee { name }
                createdAt
                updatedAt
            }
        }
        """
        result = self._graphql(query, {"id": issue_id})
        if "error" in result:
            return result
        
        issue = result.get("data", {}).get("issue", {})
        return {
            "id": issue.get("id"),
            "title": issue.get("title"),
            "description": issue.get("description"),
            "state": issue.get("state", {}).get("name"),
            "priority": issue.get("priority"),
            "assignee": issue.get("assignee", {}).get("name") if issue.get("assignee") else None,
        }
    
    def create_issue(self, title: str, team_id: str = None, description: str = None) -> Dict[str, Any]:
        """Create an issue."""
        if not title:
            return {"error": "title required"}
        if not team_id:
            return {"error": "team_id required"}
        
        query = """
        mutation($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    title
                }
            }
        }
        """
        variables = {
            "input": {
                "title": title,
                "teamId": team_id,
            }
        }
        if description:
            variables["input"]["description"] = description
        
        result = self._graphql(query, variables)
        if "error" in result:
            return result
        
        data = result.get("data", {}).get("issueCreate", {})
        if data.get("success"):
            return {"success": True, "id": data.get("issue", {}).get("id")}
        return {"error": "Failed to create issue"}
    
    def list_teams(self) -> List[Dict[str, Any]]:
        """List teams."""
        query = """
        query {
            teams {
                nodes {
                    id
                    name
                    key
                }
            }
        }
        """
        result = self._graphql(query)
        if "error" in result:
            return [result]
        
        teams = result.get("data", {}).get("teams", {}).get("nodes", [])
        return [{"id": t["id"], "name": t["name"], "key": t["key"]} for t in teams]


    def update_issue(
        self,
        issue_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        state_id: Optional[str] = None,
        priority: Optional[int] = None,
        assignee_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing issue (any subset of fields)."""
        if not issue_id:
            return {"error": "issue_id required"}

        update: Dict[str, Any] = {}
        if title is not None:
            update["title"] = title
        if description is not None:
            update["description"] = description
        if state_id is not None:
            update["stateId"] = state_id
        if priority is not None:
            update["priority"] = priority
        if assignee_id is not None:
            update["assigneeId"] = assignee_id

        if not update:
            return {"error": "no fields to update"}

        query = """
        mutation($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
                issue { id title }
            }
        }
        """
        result = self._graphql(query, {"id": issue_id, "input": update})
        if "error" in result:
            return result

        data = result.get("data", {}).get("issueUpdate", {})
        if data.get("success"):
            issue = data.get("issue") or {}
            return {"success": True, "id": issue.get("id"), "title": issue.get("title")}
        return {"error": "Failed to update issue"}

    def add_comment(self, issue_id: str, body: str) -> Dict[str, Any]:
        """Add a comment to an issue.

        When called with an OAuth token configured for ``actor=app`` mode the
        comment is posted as the application user; with a personal API key it
        is posted as the owning user.
        """
        if not issue_id:
            return {"error": "issue_id required"}
        if not body:
            return {"error": "body required"}

        query = """
        mutation($input: CommentCreateInput!) {
            commentCreate(input: $input) {
                success
                comment { id url }
            }
        }
        """
        result = self._graphql(query, {"input": {"issueId": issue_id, "body": body}})
        if "error" in result:
            return result

        data = result.get("data", {}).get("commentCreate", {})
        if data.get("success"):
            comment = data.get("comment") or {}
            return {"success": True, "id": comment.get("id"), "url": comment.get("url")}
        return {"error": "Failed to add comment"}

    def list_cycles(self, team_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """List cycles (sprints) for a team."""
        if not team_id:
            return [{"error": "team_id required"}]

        query = """
        query($id: String!, $first: Int!) {
            team(id: $id) {
                cycles(first: $first) {
                    nodes { id name number startsAt endsAt }
                }
            }
        }
        """
        result = self._graphql(query, {"id": team_id, "first": limit})
        if "error" in result:
            return [result]

        team = result.get("data", {}).get("team") or {}
        return list(team.get("cycles", {}).get("nodes", []))

    def list_issue_states(self, team_id: str) -> List[Dict[str, Any]]:
        """List workflow states for a team (Backlog/Todo/In Progress/Done/...)."""
        if not team_id:
            return [{"error": "team_id required"}]

        query = """
        query($id: String!) {
            team(id: $id) {
                states { nodes { id name type } }
            }
        }
        """
        result = self._graphql(query, {"id": team_id})
        if "error" in result:
            return [result]

        team = result.get("data", {}).get("team") or {}
        return list(team.get("states", {}).get("nodes", []))


def list_linear_issues(limit: int = 20) -> List[Dict[str, Any]]:
    """List Linear issues."""
    return LinearTool().list_issues(limit=limit)
