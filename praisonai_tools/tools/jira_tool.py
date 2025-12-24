"""Jira Tool for PraisonAI Agents.

Manage Jira issues and projects.

Usage:
    from praisonai_tools import JiraTool
    
    jira = JiraTool()
    issues = jira.search("project = PROJ AND status = Open")

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
    """Tool for managing Jira issues."""
    
    name = "jira"
    description = "Create, search, and manage Jira issues."
    
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
        super().__init__()
    
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


def jira_search(jql: str) -> List[Dict[str, Any]]:
    """Search Jira issues."""
    return JiraTool().search(jql=jql)
