"""
Repo Tool - Git repository operations.

Provides:
- Getting repository info
- Listing commits (log)
- Getting diffs
- Listing files
- Extracting changelog information
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

import sys
import os
_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

try:
    from .base import RecipeToolBase
except ImportError:
    from base import RecipeToolBase

logger = logging.getLogger(__name__)


@dataclass
class CommitInfo:
    """Information about a git commit."""
    hash: str
    short_hash: str
    author: str
    author_email: str
    date: str
    message: str
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0


@dataclass
class RepoInfo:
    """Information about a git repository."""
    path: str
    name: str
    current_branch: str
    remote_url: Optional[str] = None
    is_dirty: bool = False
    commit_count: int = 0
    last_commit: Optional[CommitInfo] = None
    tags: List[str] = field(default_factory=list)
    branches: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "name": self.name,
            "current_branch": self.current_branch,
            "remote_url": self.remote_url,
            "is_dirty": self.is_dirty,
            "commit_count": self.commit_count,
            "tags": self.tags,
            "branches": self.branches,
        }


class RepoTool(RecipeToolBase):
    """
    Git repository operations tool.
    
    Provides repository info, commit history, diffs, and file listing.
    """
    
    name = "repo_tool"
    description = "Git repository operations"
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check for git."""
        return {
            "git": self._check_binary("git"),
        }
    
    def _git(
        self,
        args: List[str],
        repo_path: Optional[Path] = None,
    ) -> str:
        """Run a git command and return output."""
        self.require_dependencies(["git"])
        
        cmd = ["git"]
        if repo_path:
            cmd.extend(["-C", str(repo_path)])
        cmd.extend(args)
        
        result = self._run_command(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"git command failed: {result.stderr}")
        
        return result.stdout.strip()
    
    def info(self, path: Union[str, Path]) -> RepoInfo:
        """
        Get information about a git repository.
        
        Args:
            path: Path to repository
            
        Returns:
            RepoInfo with repository details
        """
        path = Path(path).resolve()
        
        if not (path / ".git").exists():
            raise ValueError(f"Not a git repository: {path}")
        
        # Get basic info
        name = path.name
        
        # Current branch
        try:
            current_branch = self._git(["rev-parse", "--abbrev-ref", "HEAD"], path)
        except RuntimeError:
            current_branch = "unknown"
        
        # Remote URL
        try:
            remote_url = self._git(["remote", "get-url", "origin"], path)
        except RuntimeError:
            remote_url = None
        
        # Is dirty?
        try:
            status = self._git(["status", "--porcelain"], path)
            is_dirty = len(status) > 0
        except RuntimeError:
            is_dirty = False
        
        # Commit count
        try:
            count_str = self._git(["rev-list", "--count", "HEAD"], path)
            commit_count = int(count_str)
        except (RuntimeError, ValueError):
            commit_count = 0
        
        # Tags
        try:
            tags_str = self._git(["tag", "-l"], path)
            tags = tags_str.split("\n") if tags_str else []
        except RuntimeError:
            tags = []
        
        # Branches
        try:
            branches_str = self._git(["branch", "-a", "--format=%(refname:short)"], path)
            branches = branches_str.split("\n") if branches_str else []
        except RuntimeError:
            branches = []
        
        # Last commit
        try:
            commits = self.log(path, limit=1)
            last_commit = commits[0] if commits else None
        except RuntimeError:
            last_commit = None
        
        return RepoInfo(
            path=str(path),
            name=name,
            current_branch=current_branch,
            remote_url=remote_url,
            is_dirty=is_dirty,
            commit_count=commit_count,
            last_commit=last_commit,
            tags=tags,
            branches=branches,
        )
    
    def log(
        self,
        path: Union[str, Path],
        limit: int = 50,
        since: Optional[str] = None,
        until: Optional[str] = None,
        author: Optional[str] = None,
        grep: Optional[str] = None,
    ) -> List[CommitInfo]:
        """
        Get commit history.
        
        Args:
            path: Path to repository
            limit: Maximum number of commits
            since: Start date/ref (e.g., "2024-01-01" or "v1.0.0")
            until: End date/ref
            author: Filter by author
            grep: Filter by commit message
            
        Returns:
            List of CommitInfo objects
        """
        path = Path(path).resolve()
        
        # Format: hash|short_hash|author|email|date|message
        format_str = "%H|%h|%an|%ae|%aI|%s"
        
        args = [
            "log",
            f"--format={format_str}",
            f"-n{limit}",
        ]
        
        if since:
            args.append(f"--since={since}")
        if until:
            args.append(f"--until={until}")
        if author:
            args.append(f"--author={author}")
        if grep:
            args.append(f"--grep={grep}")
        
        output = self._git(args, path)
        
        if not output:
            return []
        
        commits = []
        for line in output.split("\n"):
            if not line:
                continue
            
            parts = line.split("|", 5)
            if len(parts) < 6:
                continue
            
            commits.append(CommitInfo(
                hash=parts[0],
                short_hash=parts[1],
                author=parts[2],
                author_email=parts[3],
                date=parts[4],
                message=parts[5],
            ))
        
        return commits
    
    def diff(
        self,
        path: Union[str, Path],
        ref1: str = "HEAD~1",
        ref2: str = "HEAD",
        name_only: bool = False,
        stat: bool = False,
    ) -> str:
        """
        Get diff between two refs.
        
        Args:
            path: Path to repository
            ref1: First ref (default: HEAD~1)
            ref2: Second ref (default: HEAD)
            name_only: Only show file names
            stat: Show diffstat
            
        Returns:
            Diff output as string
        """
        path = Path(path).resolve()
        
        args = ["diff"]
        
        if name_only:
            args.append("--name-only")
        elif stat:
            args.append("--stat")
        
        args.extend([ref1, ref2])
        
        return self._git(args, path)
    
    def files(
        self,
        path: Union[str, Path],
        ref: str = "HEAD",
        pattern: Optional[str] = None,
    ) -> List[str]:
        """
        List files in repository.
        
        Args:
            path: Path to repository
            ref: Git ref (default: HEAD)
            pattern: Glob pattern to filter files
            
        Returns:
            List of file paths
        """
        path = Path(path).resolve()
        
        args = ["ls-tree", "-r", "--name-only", ref]
        
        output = self._git(args, path)
        
        if not output:
            return []
        
        files = output.split("\n")
        
        if pattern:
            import fnmatch
            files = [f for f in files if fnmatch.fnmatch(f, pattern)]
        
        return files
    
    def get_file_content(
        self,
        path: Union[str, Path],
        file_path: str,
        ref: str = "HEAD",
    ) -> str:
        """
        Get content of a file at a specific ref.
        
        Args:
            path: Path to repository
            file_path: Path to file within repo
            ref: Git ref (default: HEAD)
            
        Returns:
            File content as string
        """
        path = Path(path).resolve()
        
        return self._git(["show", f"{ref}:{file_path}"], path)
    
    def get_changelog_commits(
        self,
        path: Union[str, Path],
        since_tag: Optional[str] = None,
    ) -> List[CommitInfo]:
        """
        Get commits for changelog generation.
        
        Args:
            path: Path to repository
            since_tag: Start from this tag (default: last tag)
            
        Returns:
            List of commits since tag
        """
        path = Path(path).resolve()
        
        # Find last tag if not specified
        if since_tag is None:
            try:
                since_tag = self._git(["describe", "--tags", "--abbrev=0", "HEAD^"], path)
            except RuntimeError:
                # No previous tag, get all commits
                return self.log(path, limit=100)
        
        # Get commits since tag
        return self.log(path, limit=500, since=since_tag)
    
    def categorize_commits(
        self,
        commits: List[CommitInfo],
    ) -> Dict[str, List[CommitInfo]]:
        """
        Categorize commits by type (feat, fix, docs, etc.).
        
        Args:
            commits: List of commits to categorize
            
        Returns:
            Dict mapping category to commits
        """
        categories = {
            "feat": [],
            "fix": [],
            "docs": [],
            "style": [],
            "refactor": [],
            "perf": [],
            "test": [],
            "chore": [],
            "other": [],
        }
        
        for commit in commits:
            msg = commit.message.lower()
            
            # Check for conventional commit prefixes
            categorized = False
            for cat in categories.keys():
                if msg.startswith(f"{cat}:") or msg.startswith(f"{cat}("):
                    categories[cat].append(commit)
                    categorized = True
                    break
            
            if not categorized:
                # Heuristic categorization
                if any(kw in msg for kw in ["add", "new", "feature", "implement"]):
                    categories["feat"].append(commit)
                elif any(kw in msg for kw in ["fix", "bug", "patch", "resolve"]):
                    categories["fix"].append(commit)
                elif any(kw in msg for kw in ["doc", "readme", "comment"]):
                    categories["docs"].append(commit)
                elif any(kw in msg for kw in ["test", "spec"]):
                    categories["test"].append(commit)
                else:
                    categories["other"].append(commit)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}


# Convenience functions
def repo_info(path: Union[str, Path], verbose: bool = False) -> RepoInfo:
    """Get repository info."""
    return RepoTool(verbose=verbose).info(path)


def repo_log(
    path: Union[str, Path],
    limit: int = 50,
    since: Optional[str] = None,
    verbose: bool = False,
) -> List[CommitInfo]:
    """Get commit history."""
    return RepoTool(verbose=verbose).log(path, limit, since)


def repo_diff(
    path: Union[str, Path],
    ref1: str = "HEAD~1",
    ref2: str = "HEAD",
    verbose: bool = False,
) -> str:
    """Get diff between refs."""
    return RepoTool(verbose=verbose).diff(path, ref1, ref2)


def repo_files(
    path: Union[str, Path],
    pattern: Optional[str] = None,
    verbose: bool = False,
) -> List[str]:
    """List files in repository."""
    return RepoTool(verbose=verbose).files(path, pattern=pattern)
