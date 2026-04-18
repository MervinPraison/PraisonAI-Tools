"""Git tools for safe read-only repository operations."""

import os
import re
import subprocess
import tempfile
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict, Any


class GitTools:
    """Git tools for safe read-only repository operations.
    
    Features:
    - Clone repositories on-demand from GitHub URLs or owner/repo format
    - Read-only git operations (no writes allowed)
    - Path escape protection
    - GitHub token support via environment variable
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """Initialize GitTools.
        
        Args:
            base_dir: Base directory for cloned repositories.
                     Defaults to temporary directory.
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path(tempfile.gettempdir()) / "praison_git_repos"
        
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # GitHub token for private repos
        self.github_token = os.getenv("GITHUB_ACCESS_TOKEN")
    
    def clone_repo(self, repo_url_or_name: str, branch: Optional[str] = None) -> str:
        """Clone or update a repository.
        
        Args:
            repo_url_or_name: Repository URL or GitHub owner/repo format
            branch: Optional branch to checkout
            
        Returns:
            Path to cloned repository
            
        Raises:
            ValueError: If repo format is invalid
            subprocess.CalledProcessError: If git operations fail
        """
        # Parse repository URL or name
        repo_url, repo_name = self._parse_repo_input(repo_url_or_name)
        
        # Safe repository path
        repo_path = self._get_safe_repo_path(repo_name)
        
        if repo_path.exists():
            # Repository exists, pull latest changes
            self._git_pull(repo_path, branch)
        else:
            # Clone repository
            self._git_clone(repo_url, repo_path, branch)
        
        return str(repo_path)
    
    def list_repos(self) -> List[str]:
        """List cloned repositories.
        
        Returns:
            List of repository names
        """
        if not self.base_dir.exists():
            return []
        
        repos = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and (item / ".git").exists():
                repos.append(item.name)
        
        return repos
    
    def repo_summary(self, repo_name: str) -> Dict[str, Any]:
        """Get repository summary information.
        
        Args:
            repo_name: Repository name
            
        Returns:
            Dictionary with repository information
        """
        repo_path = self._get_repo_path(repo_name)
        
        try:
            # Get basic info
            remote_url = self._run_git_command(
                ["remote", "get-url", "origin"], repo_path
            ).strip()
            
            current_branch = self._run_git_command(
                ["branch", "--show-current"], repo_path
            ).strip()
            
            # Get commit count
            commit_count = self._run_git_command(
                ["rev-list", "--count", "HEAD"], repo_path
            ).strip()
            
            # Get last commit info
            last_commit = self._run_git_command(
                ["log", "-1", "--pretty=format:%H|%an|%ae|%ad|%s"], repo_path
            ).strip()
            
            commit_parts = last_commit.split("|", 4)
            
            return {
                "name": repo_name,
                "remote_url": remote_url,
                "current_branch": current_branch,
                "commit_count": int(commit_count),
                "last_commit": {
                    "hash": commit_parts[0] if len(commit_parts) > 0 else "",
                    "author_name": commit_parts[1] if len(commit_parts) > 1 else "",
                    "author_email": commit_parts[2] if len(commit_parts) > 2 else "",
                    "date": commit_parts[3] if len(commit_parts) > 3 else "",
                    "message": commit_parts[4] if len(commit_parts) > 4 else "",
                }
            }
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get repo summary: {e}")
    
    def git_log(
        self, 
        repo_name: str, 
        max_count: int = 10, 
        since: Optional[str] = None,
        path: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Get git log for repository.
        
        Args:
            repo_name: Repository name
            max_count: Maximum number of commits
            since: Only commits after this date (e.g., "2024-01-01")
            path: Only commits affecting this path
            
        Returns:
            List of commit information
        """
        repo_path = self._get_repo_path(repo_name)
        
        cmd = ["log", f"--max-count={max_count}", "--pretty=format:%H|%an|%ae|%ad|%s"]
        
        if since:
            cmd.append(f"--since={since}")
        
        if path:
            safe_path = self._validate_file_path(path)
            cmd.extend(["--", safe_path])
        
        try:
            output = self._run_git_command(cmd, repo_path)
            commits = []
            
            for line in output.strip().split("\n"):
                if not line:
                    continue
                
                parts = line.split("|", 4)
                if len(parts) >= 5:
                    commits.append({
                        "hash": parts[0],
                        "author_name": parts[1],
                        "author_email": parts[2],
                        "date": parts[3],
                        "message": parts[4],
                    })
            
            return commits
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get git log: {e}")
    
    def git_diff(
        self, 
        repo_name: str, 
        commit1: str, 
        commit2: Optional[str] = None,
        path: Optional[str] = None
    ) -> str:
        """Get git diff between commits.
        
        Args:
            repo_name: Repository name
            commit1: First commit hash
            commit2: Second commit hash (if None, compares with working tree)
            path: Only diff for this path
            
        Returns:
            Diff output
        """
        repo_path = self._get_repo_path(repo_name)
        
        cmd = ["diff"]
        
        if commit2:
            cmd.extend([commit1, commit2])
        else:
            cmd.append(commit1)
        
        if path:
            safe_path = self._validate_file_path(path)
            cmd.extend(["--", safe_path])
        
        try:
            return self._run_git_command(cmd, repo_path)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get git diff: {e}")
    
    def git_show(self, repo_name: str, commit: str, path: Optional[str] = None) -> str:
        """Show git commit or file content.
        
        Args:
            repo_name: Repository name
            commit: Commit hash
            path: Optional file path
            
        Returns:
            Commit or file content
        """
        repo_path = self._get_repo_path(repo_name)
        
        if path:
            safe_path = self._validate_file_path(path)
            ref = f"{commit}:{safe_path}"
        else:
            ref = commit
        
        try:
            return self._run_git_command(["show", ref], repo_path)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to show git object: {e}")
    
    def git_blame(self, repo_name: str, file_path: str) -> List[Dict[str, str]]:
        """Get git blame for a file.
        
        Args:
            repo_name: Repository name
            file_path: File path to blame
            
        Returns:
            List of blame information for each line
        """
        repo_path = self._get_repo_path(repo_name)
        safe_path = self._validate_file_path(file_path)
        
        try:
            output = self._run_git_command(
                ["blame", "--porcelain", safe_path], repo_path
            )
            
            blame_data = []
            lines = output.split("\n")
            i = 0
            
            while i < len(lines):
                line = lines[i]
                if not line or line.startswith("\t"):
                    i += 1
                    continue
                
                # Parse blame entry
                parts = line.split(" ", 3)
                if len(parts) >= 3:
                    commit_hash = parts[0]
                    line_num = int(parts[2])
                    
                    # Find content line
                    content = ""
                    for j in range(i + 1, len(lines)):
                        if lines[j].startswith("\t"):
                            content = lines[j][1:]  # Remove leading tab
                            break
                    
                    blame_data.append({
                        "commit": commit_hash,
                        "line_number": line_num,
                        "content": content
                    })
                
                i += 1
            
            return blame_data
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get git blame: {e}")
    
    def git_branches(self, repo_name: str) -> List[str]:
        """Get list of branches.
        
        Args:
            repo_name: Repository name
            
        Returns:
            List of branch names
        """
        repo_path = self._get_repo_path(repo_name)
        
        try:
            output = self._run_git_command(["branch", "-r"], repo_path)
            branches = []
            
            for line in output.strip().split("\n"):
                if line and not "origin/HEAD" in line:
                    branch = line.strip().replace("origin/", "")
                    branches.append(branch)
            
            return branches
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get branches: {e}")
    
    def read_file(self, repo_name: str, file_path: str, commit: str = "HEAD") -> str:
        """Read file content from repository.
        
        Args:
            repo_name: Repository name
            file_path: File path relative to repo root
            commit: Commit hash or reference (default: HEAD)
            
        Returns:
            File content
        """
        safe_path = self._validate_file_path(file_path)
        return self.git_show(repo_name, commit, safe_path)
    
    def get_github_remote(self, repo_name: str) -> Optional[Dict[str, str]]:
        """Extract GitHub owner and repo from remote URL.
        
        Args:
            repo_name: Repository name
            
        Returns:
            Dict with 'owner' and 'repo' keys, or None if not GitHub
        """
        try:
            repo_path = self._get_repo_path(repo_name)
            remote_url = self._run_git_command(
                ["remote", "get-url", "origin"], repo_path
            ).strip()
            
            # Parse GitHub URL
            github_match = re.match(
                r"(?:https://github\.com/|git@github\.com:)([^/]+)/([^/]+?)(?:\.git)?/?$",
                remote_url
            )
            
            if github_match:
                return {
                    "owner": github_match.group(1),
                    "repo": github_match.group(2)
                }
            
            return None
            
        except subprocess.CalledProcessError:
            return None
    
    def _parse_repo_input(self, repo_input: str) -> tuple[str, str]:
        """Parse repository input to URL and name.
        
        Args:
            repo_input: Repository URL or owner/repo format
            
        Returns:
            Tuple of (url, name)
        """
        if repo_input.startswith(("https://", "git@")):
            # Full URL
            repo_url = repo_input
            
            # Extract name from URL
            if repo_input.startswith("https://github.com/"):
                path_part = repo_input.replace("https://github.com/", "")
            elif repo_input.startswith("git@github.com:"):
                path_part = repo_input.replace("git@github.com:", "")
            else:
                raise ValueError("Only GitHub URLs are supported")
            
            path_part = path_part.rstrip("/").replace(".git", "")
            repo_name = path_part.replace("/", "_")
            
        elif "/" in repo_input:
            # owner/repo format
            if repo_input.count("/") != 1:
                raise ValueError("Invalid owner/repo format")
            
            owner, repo = repo_input.split("/")
            repo_name = f"{owner}_{repo}"
            
            # Build GitHub URL with token if available
            if self.github_token:
                repo_url = f"https://{self.github_token}@github.com/{owner}/{repo}.git"
            else:
                repo_url = f"https://github.com/{owner}/{repo}.git"
        else:
            raise ValueError("Invalid repository format. Use 'owner/repo' or full URL")
        
        return repo_url, repo_name
    
    def _get_safe_repo_path(self, repo_name: str) -> Path:
        """Get safe repository path, preventing path traversal."""
        # Sanitize repo name
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", repo_name)
        repo_path = self.base_dir / safe_name
        
        # Ensure path is under base_dir
        if not repo_path.is_relative_to(self.base_dir):
            raise ValueError("Invalid repository path")
        
        return repo_path
    
    def _get_repo_path(self, repo_name: str) -> Path:
        """Get repository path and validate it exists."""
        repo_path = self._get_safe_repo_path(repo_name)
        
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository not found: {repo_name}")
        
        if not (repo_path / ".git").exists():
            raise ValueError(f"Not a git repository: {repo_name}")
        
        return repo_path
    
    def _validate_file_path(self, file_path: str) -> str:
        """Validate file path is safe (no path traversal)."""
        # Check for absolute paths
        if file_path.startswith("/"):
            raise ValueError("Invalid file path")
        
        # Remove any leading slashes
        safe_path = file_path.lstrip("/")
        
        # Check for path traversal attempts
        if ".." in safe_path:
            raise ValueError("Invalid file path")
        
        # Basic path validation - above checks already prevent most traversal attacks
        
        return safe_path
    
    def _git_clone(self, repo_url: str, repo_path: Path, branch: Optional[str] = None):
        """Clone repository."""
        cmd = ["git", "clone"]
        
        if branch:
            cmd.extend(["-b", branch])
        
        cmd.extend([repo_url, str(repo_path)])
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to clone repository: {e.stderr}")
    
    def _git_pull(self, repo_path: Path, branch: Optional[str] = None):
        """Pull latest changes."""
        if branch:
            # Checkout specific branch
            self._run_git_command(["checkout", branch], repo_path)
        
        # Pull latest changes
        self._run_git_command(["pull"], repo_path)
    
    def _run_git_command(self, cmd: List[str], repo_path: Path) -> str:
        """Run git command in repository directory."""
        full_cmd = ["git"] + cmd
        
        try:
            result = subprocess.run(
                full_cmd,
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise subprocess.CalledProcessError(
                e.returncode, e.cmd, e.stdout, e.stderr
            )