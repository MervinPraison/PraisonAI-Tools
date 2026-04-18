"""Unit tests for GitTools."""

import os
import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

from praisonai_tools.tools.git_tools import GitTools


class TestGitToolsInit:
    """Test GitTools initialization."""
    
    def test_init_with_base_dir(self):
        """Test initialization with custom base directory."""
        base_dir = "/tmp/custom_repos"
        git_tools = GitTools(base_dir=base_dir)
        
        assert git_tools.base_dir == Path(base_dir)
    
    def test_init_without_base_dir(self):
        """Test initialization without base directory."""
        git_tools = GitTools()
        
        # Should use temp directory
        assert "praison_git_repos" in str(git_tools.base_dir)
        assert git_tools.base_dir.exists()
    
    def test_init_with_github_token(self):
        """Test initialization with GitHub token."""
        with patch.dict(os.environ, {"GITHUB_ACCESS_TOKEN": "test_token"}):
            git_tools = GitTools()
            assert git_tools.github_token == "test_token"
    
    def test_init_without_github_token(self):
        """Test initialization without GitHub token."""
        with patch.dict(os.environ, {}, clear=True):
            git_tools = GitTools()
            assert git_tools.github_token is None


class TestParseRepoInput:
    """Test repository input parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.git_tools = GitTools()
    
    def test_parse_https_url(self):
        """Test parsing HTTPS GitHub URL."""
        url = "https://github.com/owner/repo.git"
        repo_url, repo_name = self.git_tools._parse_repo_input(url)
        
        assert repo_url == url
        assert repo_name == "owner_repo"
    
    def test_parse_ssh_url(self):
        """Test parsing SSH GitHub URL."""
        url = "git@github.com:owner/repo.git"
        repo_url, repo_name = self.git_tools._parse_repo_input(url)
        
        assert repo_url == url
        assert repo_name == "owner_repo"
    
    def test_parse_owner_repo_format(self):
        """Test parsing owner/repo format."""
        repo_input = "owner/repo"
        repo_url, repo_name = self.git_tools._parse_repo_input(repo_input)
        
        assert repo_url == "https://github.com/owner/repo.git"
        assert repo_name == "owner_repo"
    
    def test_parse_owner_repo_with_token(self):
        """Test parsing owner/repo format with token."""
        with patch.object(self.git_tools, 'github_token', "test_token"):
            repo_input = "owner/repo"
            repo_url, repo_name = self.git_tools._parse_repo_input(repo_input)
            
            assert repo_url == "https://test_token@github.com/owner/repo.git"
            assert repo_name == "owner_repo"
    
    def test_parse_non_github_url(self):
        """Test parsing non-GitHub URL raises error."""
        url = "https://gitlab.com/owner/repo.git"
        
        with pytest.raises(ValueError, match="Only GitHub URLs are supported"):
            self.git_tools._parse_repo_input(url)
    
    def test_parse_invalid_owner_repo_format(self):
        """Test parsing invalid owner/repo format raises error."""
        invalid_inputs = [
            "owner",  # Missing repo
            "owner/repo/extra",  # Too many slashes
            "",  # Empty
        ]
        
        for invalid_input in invalid_inputs:
            with pytest.raises(ValueError):
                self.git_tools._parse_repo_input(invalid_input)
    
    def test_parse_url_without_git_suffix(self):
        """Test parsing URL without .git suffix."""
        url = "https://github.com/owner/repo"
        repo_url, repo_name = self.git_tools._parse_repo_input(url)
        
        assert repo_url == url
        assert repo_name == "owner_repo"


class TestSafety:
    """Test safety features."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.git_tools = GitTools()
    
    def test_get_safe_repo_path(self):
        """Test safe repository path generation."""
        repo_name = "owner_repo"
        repo_path = self.git_tools._get_safe_repo_path(repo_name)
        
        assert repo_path.is_relative_to(self.git_tools.base_dir)
        assert repo_path.name == repo_name
    
    def test_get_safe_repo_path_sanitizes_name(self):
        """Test repository name sanitization."""
        repo_name = "owner@repo/with#special$chars"
        repo_path = self.git_tools._get_safe_repo_path(repo_name)
        
        # Should sanitize special characters
        assert "@" not in repo_path.name
        assert "/" not in repo_path.name
        assert "#" not in repo_path.name
        assert "$" not in repo_path.name
    
    def test_validate_file_path_safe(self):
        """Test file path validation for safe paths."""
        safe_paths = [
            "README.md",
            "src/main.py", 
            "docs/api.md",
            "tests/test_file.py"
        ]
        
        for safe_path in safe_paths:
            result = self.git_tools._validate_file_path(safe_path)
            assert result == safe_path
    
    def test_validate_file_path_unsafe(self):
        """Test file path validation for unsafe paths."""
        unsafe_paths = [
            "../etc/passwd",
            "../../secret.txt",
            "/absolute/path.txt",
            "dir/../../../escape.txt"
        ]
        
        for unsafe_path in unsafe_paths:
            with pytest.raises(ValueError, match="Invalid file path"):
                self.git_tools._validate_file_path(unsafe_path)
    
    def test_validate_file_path_removes_leading_slash(self):
        """Test file path validation removes leading slashes."""
        result = self.git_tools._validate_file_path("/src/main.py")
        assert result == "src/main.py"


class TestGitOperations:
    """Test git operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.base_dir = tmpdir
            self.git_tools = GitTools(base_dir=tmpdir)
    
    @patch('subprocess.run')
    def test_git_clone(self, mock_run):
        """Test git clone operation."""
        mock_run.return_value = Mock(returncode=0)
        
        repo_url = "https://github.com/owner/repo.git"
        repo_path = Path(self.base_dir) / "test_repo"
        
        self.git_tools._git_clone(repo_url, repo_path)
        
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[:2] == ["git", "clone"]
        assert repo_url in call_args
        assert str(repo_path) in call_args
    
    @patch('subprocess.run')
    def test_git_clone_with_branch(self, mock_run):
        """Test git clone with specific branch."""
        mock_run.return_value = Mock(returncode=0)
        
        repo_url = "https://github.com/owner/repo.git"
        repo_path = Path(self.base_dir) / "test_repo"
        branch = "develop"
        
        self.git_tools._git_clone(repo_url, repo_path, branch)
        
        call_args = mock_run.call_args[0][0]
        assert "-b" in call_args
        assert branch in call_args
    
    @patch('subprocess.run')
    def test_git_clone_failure(self, mock_run):
        """Test git clone failure handling."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git", "clone"], stderr="Repository not found"
        )
        
        repo_url = "https://github.com/owner/nonexistent.git"
        repo_path = Path(self.base_dir) / "test_repo"
        
        with pytest.raises(RuntimeError, match="Failed to clone repository"):
            self.git_tools._git_clone(repo_url, repo_path)
    
    @patch('subprocess.run')
    def test_run_git_command_success(self, mock_run):
        """Test successful git command execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="command output"
        )
        
        repo_path = Path(self.base_dir) / "test_repo"
        result = self.git_tools._run_git_command(["status"], repo_path)
        
        assert result == "command output"
        mock_run.assert_called_once()
        call_args, call_kwargs = mock_run.call_args
        assert call_args[0] == ["git", "status"]
        assert call_kwargs["cwd"] == repo_path
    
    @patch('subprocess.run')
    def test_run_git_command_failure(self, mock_run):
        """Test git command failure handling."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git", "status"], stdout="", stderr="not a git repository"
        )
        
        repo_path = Path(self.base_dir) / "test_repo"
        
        with pytest.raises(subprocess.CalledProcessError):
            self.git_tools._run_git_command(["status"], repo_path)
    
    def test_get_repo_path_nonexistent(self):
        """Test getting path for nonexistent repository."""
        with pytest.raises(FileNotFoundError, match="Repository not found"):
            self.git_tools._get_repo_path("nonexistent_repo")


class TestRepositoryMethods:
    """Test repository management methods."""
    
    def setup_method(self):
        """Set up test fixtures.""" 
        self.git_tools = GitTools()
    
    @patch.object(GitTools, '_parse_repo_input')
    @patch.object(GitTools, '_get_safe_repo_path')
    @patch.object(GitTools, '_git_clone')
    @patch.object(GitTools, '_git_pull')
    def test_clone_repo_new(self, mock_pull, mock_clone, mock_path, mock_parse):
        """Test cloning new repository."""
        mock_parse.return_value = ("https://github.com/owner/repo.git", "owner_repo")
        mock_path.return_value = Path("/tmp/owner_repo")
        
        # Repository doesn't exist
        with patch.object(Path, 'exists', return_value=False):
            result = self.git_tools.clone_repo("owner/repo")
        
        assert result == str(Path("/tmp/owner_repo"))
        mock_clone.assert_called_once()
        mock_pull.assert_not_called()
    
    @patch.object(GitTools, '_parse_repo_input')
    @patch.object(GitTools, '_get_safe_repo_path')
    @patch.object(GitTools, '_git_clone')
    @patch.object(GitTools, '_git_pull')
    def test_clone_repo_existing(self, mock_pull, mock_clone, mock_path, mock_parse):
        """Test updating existing repository."""
        mock_parse.return_value = ("https://github.com/owner/repo.git", "owner_repo")
        mock_path.return_value = Path("/tmp/owner_repo")
        
        # Repository exists
        with patch.object(Path, 'exists', return_value=True):
            result = self.git_tools.clone_repo("owner/repo")
        
        assert result == str(Path("/tmp/owner_repo"))
        mock_clone.assert_not_called()
        mock_pull.assert_called_once()
    
    def test_list_repos_empty(self):
        """Test listing repositories when none exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            git_tools = GitTools(base_dir=tmpdir)
            repos = git_tools.list_repos()
            assert repos == []
    
    def test_list_repos_with_repos(self):
        """Test listing repositories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            git_tools = GitTools(base_dir=tmpdir)
            
            # Create fake git repositories
            (Path(tmpdir) / "repo1" / ".git").mkdir(parents=True)
            (Path(tmpdir) / "repo2" / ".git").mkdir(parents=True)
            (Path(tmpdir) / "not_a_repo").mkdir()  # Should be ignored
            
            repos = git_tools.list_repos()
            assert sorted(repos) == ["repo1", "repo2"]
    
    @patch.object(GitTools, '_run_git_command')
    @patch.object(GitTools, '_get_repo_path')
    def test_repo_summary(self, mock_get_path, mock_run_git):
        """Test getting repository summary."""
        repo_path = Path("/tmp/test_repo")
        mock_get_path.return_value = repo_path
        
        # Mock git command outputs
        mock_run_git.side_effect = [
            "https://github.com/owner/repo.git",  # remote url
            "main",  # current branch
            "42",  # commit count
            "abc123|John Doe|john@example.com|2024-01-01|Initial commit"  # last commit
        ]
        
        summary = self.git_tools.repo_summary("test_repo")
        
        assert summary["name"] == "test_repo"
        assert summary["remote_url"] == "https://github.com/owner/repo.git"
        assert summary["current_branch"] == "main"
        assert summary["commit_count"] == 42
        assert summary["last_commit"]["hash"] == "abc123"
        assert summary["last_commit"]["author_name"] == "John Doe"
        assert summary["last_commit"]["message"] == "Initial commit"
    
    @patch.object(GitTools, '_run_git_command')
    @patch.object(GitTools, '_get_repo_path')
    def test_git_log(self, mock_get_path, mock_run_git):
        """Test git log retrieval."""
        repo_path = Path("/tmp/test_repo")
        mock_get_path.return_value = repo_path
        
        mock_run_git.return_value = (
            "abc123|John Doe|john@example.com|2024-01-01|Initial commit\n"
            "def456|Jane Doe|jane@example.com|2024-01-02|Second commit"
        )
        
        commits = self.git_tools.git_log("test_repo", max_count=2)
        
        assert len(commits) == 2
        assert commits[0]["hash"] == "abc123"
        assert commits[0]["author_name"] == "John Doe"
        assert commits[1]["hash"] == "def456"
        assert commits[1]["author_name"] == "Jane Doe"
    
    @patch.object(GitTools, '_run_git_command')
    @patch.object(GitTools, '_get_repo_path')
    def test_git_diff(self, mock_get_path, mock_run_git):
        """Test git diff retrieval."""
        repo_path = Path("/tmp/test_repo")
        mock_get_path.return_value = repo_path
        
        mock_run_git.return_value = "diff output"
        
        result = self.git_tools.git_diff("test_repo", "abc123", "def456")
        
        assert result == "diff output"
        mock_run_git.assert_called_once_with(["diff", "abc123", "def456"], repo_path)
    
    @patch.object(GitTools, '_run_git_command')
    @patch.object(GitTools, '_get_repo_path')
    def test_git_show(self, mock_get_path, mock_run_git):
        """Test git show command."""
        repo_path = Path("/tmp/test_repo")
        mock_get_path.return_value = repo_path
        
        mock_run_git.return_value = "file content"
        
        result = self.git_tools.git_show("test_repo", "abc123", "README.md")
        
        assert result == "file content"
        mock_run_git.assert_called_once_with(["show", "abc123:README.md"], repo_path)
    
    @patch.object(GitTools, '_run_git_command')
    @patch.object(GitTools, '_get_repo_path')
    def test_git_branches(self, mock_get_path, mock_run_git):
        """Test git branches listing."""
        repo_path = Path("/tmp/test_repo")
        mock_get_path.return_value = repo_path
        
        mock_run_git.return_value = (
            "  origin/main\n"
            "  origin/develop\n" 
            "  origin/HEAD -> origin/main"
        )
        
        branches = self.git_tools.git_branches("test_repo")
        
        assert sorted(branches) == ["develop", "main"]
    
    @patch.object(GitTools, '_run_git_command')
    @patch.object(GitTools, '_get_repo_path')
    def test_get_github_remote(self, mock_get_path, mock_run_git):
        """Test GitHub remote parsing."""
        repo_path = Path("/tmp/test_repo")
        mock_get_path.return_value = repo_path
        
        # Test HTTPS URL
        mock_run_git.return_value = "https://github.com/owner/repo.git"
        result = self.git_tools.get_github_remote("test_repo")
        
        assert result == {"owner": "owner", "repo": "repo"}
        
        # Test SSH URL
        mock_run_git.return_value = "git@github.com:owner/repo.git"
        result = self.git_tools.get_github_remote("test_repo")
        
        assert result == {"owner": "owner", "repo": "repo"}
        
        # Test non-GitHub URL
        mock_run_git.return_value = "https://gitlab.com/owner/repo.git"
        result = self.git_tools.get_github_remote("test_repo")
        
        assert result is None