"""GitHub Tool for PraisonAI Agents.

Interact with GitHub repositories, issues, pull requests, and more.

Usage:
    from praisonai_tools import GitHubTool
    
    gh = GitHubTool()  # Uses GITHUB_TOKEN env var
    
    # Search repositories
    repos = gh.search_repos("machine learning python")
    
    # Create issue
    gh.create_issue(repo="owner/repo", title="Bug", body="Description")

Environment Variables:
    GITHUB_TOKEN: GitHub Personal Access Token
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class GitHubTool(BaseTool):
    """Tool for interacting with GitHub."""
    
    name = "github"
    description = "Interact with GitHub - search repos, create issues, manage pull requests."
    
    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_ACCESS_TOKEN")
        self.base_url = base_url
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            if not self.token:
                raise ValueError("GITHUB_TOKEN not configured.")
            try:
                from github import Github, Auth
            except ImportError:
                raise ImportError("PyGithub not installed. Install with: pip install PyGithub")
            auth = Auth.Token(self.token)
            self._client = Github(base_url=self.base_url, auth=auth) if self.base_url else Github(auth=auth)
        return self._client
    
    def run(
        self,
        action: str = "search_repos",
        query: Optional[str] = None,
        repo: Optional[str] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        path: Optional[str] = None,
        number: Optional[int] = None,
        limit: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        if action == "search_repos":
            return self.search_repos(query=query, limit=limit)
        elif action == "list_repos":
            return self.list_repos(limit=limit)
        elif action == "get_repo":
            return self.get_repo(repo=repo)
        elif action == "list_issues":
            return self.list_issues(repo=repo, limit=limit)
        elif action == "get_issue":
            return self.get_issue(repo=repo, number=number)
        elif action == "create_issue":
            return self.create_issue(repo=repo, title=title, body=body, **kwargs)
        elif action == "list_prs":
            return self.list_pull_requests(repo=repo, limit=limit)
        elif action == "get_file":
            return self.get_file(repo=repo, path=path, **kwargs)
        elif action == "list_branches":
            return self.list_branches(repo=repo)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search_repos(self, query: str, sort: str = "stars", order: str = "desc", limit: int = 10) -> List[Dict[str, Any]]:
        if not query:
            return [{"error": "Query is required"}]
        try:
            from github import GithubException
            repos = self.client.search_repositories(query=query, sort=sort, order=order)
            results = []
            for repo in repos[:limit]:
                results.append({
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "url": repo.html_url,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "language": repo.language,
                })
            return results
        except GithubException as e:
            return [{"error": str(e)}]
        except Exception as e:
            return [{"error": str(e)}]
    
    def list_repos(self, limit: int = 30) -> List[Dict[str, Any]]:
        try:
            from github import GithubException
            repos = self.client.get_user().get_repos()
            results = []
            for repo in repos[:limit]:
                results.append({
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "url": repo.html_url,
                    "private": repo.private,
                    "stars": repo.stargazers_count,
                })
            return results
        except GithubException as e:
            return [{"error": str(e)}]
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_repo(self, repo: str) -> Dict[str, Any]:
        if not repo:
            return {"error": "Repository name required (format: owner/repo)"}
        try:
            from github import GithubException
            r = self.client.get_repo(repo)
            return {
                "full_name": r.full_name,
                "description": r.description,
                "url": r.html_url,
                "stars": r.stargazers_count,
                "forks": r.forks_count,
                "language": r.language,
                "default_branch": r.default_branch,
                "open_issues": r.open_issues_count,
            }
        except GithubException as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}
    
    def list_issues(self, repo: str, state: str = "open", limit: int = 10) -> List[Dict[str, Any]]:
        if not repo:
            return [{"error": "Repository name required"}]
        try:
            from github import GithubException
            r = self.client.get_repo(repo)
            issues = r.get_issues(state=state)
            results = []
            for issue in issues[:limit]:
                if issue.pull_request:
                    continue
                results.append({
                    "number": issue.number,
                    "title": issue.title,
                    "state": issue.state,
                    "url": issue.html_url,
                    "user": issue.user.login,
                })
            return results
        except GithubException as e:
            return [{"error": str(e)}]
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_issue(self, repo: str, number: int) -> Dict[str, Any]:
        if not repo or not number:
            return {"error": "Repository and issue number required"}
        try:
            from github import GithubException
            r = self.client.get_repo(repo)
            issue = r.get_issue(number)
            return {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "url": issue.html_url,
                "user": issue.user.login,
                "comments": issue.comments,
            }
        except GithubException as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}
    
    def create_issue(self, repo: str, title: str, body: Optional[str] = None, labels: Optional[List[str]] = None, assignees: Optional[List[str]] = None) -> Dict[str, Any]:
        if not repo or not title:
            return {"error": "Repository and title required"}
        try:
            from github import GithubException
            r = self.client.get_repo(repo)
            kwargs = {"title": title}
            if body:
                kwargs["body"] = body
            if labels:
                kwargs["labels"] = labels
            if assignees:
                kwargs["assignees"] = assignees
            issue = r.create_issue(**kwargs)
            return {"success": True, "number": issue.number, "url": issue.html_url}
        except GithubException as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}
    
    def list_pull_requests(self, repo: str, state: str = "open", limit: int = 10) -> List[Dict[str, Any]]:
        if not repo:
            return [{"error": "Repository name required"}]
        try:
            from github import GithubException
            r = self.client.get_repo(repo)
            prs = r.get_pulls(state=state)
            results = []
            for pr in prs[:limit]:
                results.append({
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state,
                    "url": pr.html_url,
                    "user": pr.user.login,
                })
            return results
        except GithubException as e:
            return [{"error": str(e)}]
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_file(self, repo: str, path: str, ref: Optional[str] = None) -> Dict[str, Any]:
        if not repo or not path:
            return {"error": "Repository and path required"}
        try:
            from github import GithubException
            r = self.client.get_repo(repo)
            kwargs = {"path": path}
            if ref:
                kwargs["ref"] = ref
            content = r.get_contents(**kwargs)
            if not isinstance(content, list):
                return {
                    "path": content.path,
                    "name": content.name,
                    "size": content.size,
                    "content": content.decoded_content.decode("utf-8") if content.size < 100000 else "[Too large]",
                }
            return {"path": path, "type": "directory", "contents": [{"name": f.name, "type": f.type} for f in content]}
        except GithubException as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}
    
    def list_branches(self, repo: str) -> List[Dict[str, Any]]:
        if not repo:
            return [{"error": "Repository name required"}]
        try:
            from github import GithubException
            r = self.client.get_repo(repo)
            return [{"name": b.name, "sha": b.commit.sha, "protected": b.protected} for b in r.get_branches()]
        except GithubException as e:
            return [{"error": str(e)}]
        except Exception as e:
            return [{"error": str(e)}]


def search_github_repos(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    return GitHubTool().search_repos(query=query, limit=limit)


def get_github_repo(repo: str) -> Dict[str, Any]:
    return GitHubTool().get_repo(repo=repo)


def create_github_issue(repo: str, title: str, body: Optional[str] = None) -> Dict[str, Any]:
    return GitHubTool().create_issue(repo=repo, title=title, body=body)
