"""Tests for RepoTool."""

import subprocess
import pytest

from praisonai_tools.recipe_tools.repo_tool import RepoTool, repo_info, repo_log


class TestRepoTool:
    """Unit tests for RepoTool."""
    
    @pytest.fixture
    def tool(self):
        return RepoTool(verbose=True)
    
    @pytest.fixture
    def git_repo(self, temp_dir):
        """Create a temporary git repository."""
        repo_dir = temp_dir / "test_repo"
        repo_dir.mkdir()
        
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, capture_output=True)
        
        # Create some files and commits
        (repo_dir / "file1.txt").write_text("content 1")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: initial commit"], cwd=repo_dir, capture_output=True)
        
        (repo_dir / "file2.txt").write_text("content 2")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "fix: add file2"], cwd=repo_dir, capture_output=True)
        
        return repo_dir
    
    @pytest.mark.unit
    def test_check_dependencies(self, tool):
        """Test dependency checking."""
        deps = tool.check_dependencies()
        assert "git" in deps
    
    @pytest.mark.requires_git
    def test_info(self, tool, git_repo, has_git):
        """Test getting repo info."""
        if not has_git:
            pytest.skip("git not available")
        
        result = tool.info(git_repo)
        
        assert result.path == str(git_repo)
        assert result.name == "test_repo"
        assert result.commit_count >= 2
    
    @pytest.mark.requires_git
    def test_log(self, tool, git_repo, has_git):
        """Test getting commit log."""
        if not has_git:
            pytest.skip("git not available")
        
        commits = tool.log(git_repo, limit=10)
        
        assert len(commits) >= 2
        assert commits[0].message  # Most recent commit
    
    @pytest.mark.requires_git
    def test_diff(self, tool, git_repo, has_git):
        """Test getting diff."""
        if not has_git:
            pytest.skip("git not available")
        
        diff = tool.diff(git_repo, "HEAD~1", "HEAD")
        
        assert "file2.txt" in diff
    
    @pytest.mark.requires_git
    def test_files(self, tool, git_repo, has_git):
        """Test listing files."""
        if not has_git:
            pytest.skip("git not available")
        
        files = tool.files(git_repo)
        
        assert "file1.txt" in files
        assert "file2.txt" in files
    
    @pytest.mark.requires_git
    def test_categorize_commits(self, tool, git_repo, has_git):
        """Test commit categorization."""
        if not has_git:
            pytest.skip("git not available")
        
        commits = tool.log(git_repo)
        categories = tool.categorize_commits(commits)
        
        assert "feat" in categories or "fix" in categories
    
    @pytest.mark.unit
    def test_not_a_repo(self, tool, temp_dir):
        """Test error on non-repo directory."""
        with pytest.raises(ValueError, match="Not a git repository"):
            tool.info(temp_dir)


class TestRepoToolConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.fixture
    def git_repo(self, temp_dir):
        """Create a temporary git repository."""
        repo_dir = temp_dir / "test_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, capture_output=True)
        (repo_dir / "file.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_dir, capture_output=True)
        return repo_dir
    
    @pytest.mark.requires_git
    def test_repo_info(self, git_repo, has_git):
        """Test repo_info function."""
        if not has_git:
            pytest.skip("git not available")
        
        result = repo_info(git_repo)
        assert result.commit_count >= 1
    
    @pytest.mark.requires_git
    def test_repo_log(self, git_repo, has_git):
        """Test repo_log function."""
        if not has_git:
            pytest.skip("git not available")
        
        commits = repo_log(git_repo)
        assert len(commits) >= 1
