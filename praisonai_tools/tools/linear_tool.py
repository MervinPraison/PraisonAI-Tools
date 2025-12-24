"""Linear Tool for PraisonAI Agents.

Manage Linear issues and projects.

Usage:
    from praisonai_tools import LinearTool
    
    linear = LinearTool()
    issues = linear.list_issues()

Environment Variables:
    LINEAR_API_KEY: Linear API key
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
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LINEAR_API_KEY")
        self.api_url = "https://api.linear.app/graphql"
        super().__init__()
    
    def _graphql(self, query: str, variables: Dict = None) -> Dict:
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        if not self.api_key:
            return {"error": "LINEAR_API_KEY required"}
        
        try:
            resp = requests.post(
                self.api_url,
                headers={"Authorization": self.api_key, "Content-Type": "application/json"},
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
        elif action == "list_teams":
            return self.list_teams()
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


def list_linear_issues(limit: int = 20) -> List[Dict[str, Any]]:
    """List Linear issues."""
    return LinearTool().list_issues(limit=limit)
