"""Bitbucket Tool for PraisonAI Agents.

Manage Bitbucket repositories and pull requests.

Usage:
    from praisonai_tools import BitbucketTool
    
    bb = BitbucketTool()
    repos = bb.list_repos(workspace="myworkspace")

Environment Variables:
    BITBUCKET_USERNAME: Bitbucket username
    BITBUCKET_APP_PASSWORD: Bitbucket app password
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class BitbucketTool(BaseTool):
    """Tool for Bitbucket operations."""
    
    name = "bitbucket"
    description = "Manage Bitbucket repositories and pull requests."
    
    def __init__(
        self,
        username: Optional[str] = None,
        app_password: Optional[str] = None,
    ):
        self.username = username or os.getenv("BITBUCKET_USERNAME")
        self.app_password = app_password or os.getenv("BITBUCKET_APP_PASSWORD")
        super().__init__()
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        if not self.username or not self.app_password:
            return {"error": "BITBUCKET_USERNAME and BITBUCKET_APP_PASSWORD required"}
        
        url = f"https://api.bitbucket.org/2.0/{endpoint}"
        auth = (self.username, self.app_password)
        
        try:
            if method == "GET":
                resp = requests.get(url, auth=auth, timeout=10)
            elif method == "POST":
                resp = requests.post(url, auth=auth, json=data, timeout=10)
            else:
                return {"error": f"Unknown method: {method}"}
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "list_repos",
        workspace: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list_repos":
            return self.list_repos(workspace=workspace)
        elif action == "get_repo":
            return self.get_repo(workspace=workspace, repo_slug=kwargs.get("repo_slug"))
        elif action == "list_prs":
            return self.list_prs(workspace=workspace, repo_slug=kwargs.get("repo_slug"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_repos(self, workspace: str) -> List[Dict[str, Any]]:
        """List repositories."""
        if not workspace:
            return [{"error": "workspace is required"}]
        result = self._request("GET", f"repositories/{workspace}")
        if "error" in result:
            return [result]
        return [{"name": r["name"], "slug": r["slug"]} for r in result.get("values", [])]
    
    def get_repo(self, workspace: str, repo_slug: str) -> Dict[str, Any]:
        """Get repository details."""
        if not workspace or not repo_slug:
            return {"error": "workspace and repo_slug are required"}
        return self._request("GET", f"repositories/{workspace}/{repo_slug}")
    
    def list_prs(self, workspace: str, repo_slug: str) -> List[Dict[str, Any]]:
        """List pull requests."""
        if not workspace or not repo_slug:
            return [{"error": "workspace and repo_slug are required"}]
        result = self._request("GET", f"repositories/{workspace}/{repo_slug}/pullrequests")
        if "error" in result:
            return [result]
        return [{"id": pr["id"], "title": pr["title"], "state": pr["state"]} for pr in result.get("values", [])]


def bitbucket_list_repos(workspace: str) -> List[Dict[str, Any]]:
    """List Bitbucket repos."""
    return BitbucketTool().list_repos(workspace=workspace)
