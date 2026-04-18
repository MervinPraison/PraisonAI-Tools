"""Tests for backend workspace safety."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock

try:
    from praisonai_tools.video.motion_graphics.backend_html import HtmlRenderBackend
    from praisonai_tools.video.motion_graphics.protocols import RenderOpts
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False


@pytest.mark.skipif(not BACKEND_AVAILABLE, reason="Motion graphics backend not available")
class TestBackendSafety:
    """Test workspace safety features."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.backend = HtmlRenderBackend(base_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_safe_workspace_under_base_dir(self):
        """Test workspace under base directory is considered safe."""
        safe_workspace = self.temp_dir / "workspace"
        safe_workspace.mkdir()
        
        assert self.backend._is_safe_workspace(safe_workspace)
    
    def test_unsafe_workspace_outside_base_dir(self):
        """Test workspace outside base directory is rejected."""
        # Try to escape to parent directory
        unsafe_workspace = self.temp_dir.parent / "escaped"
        
        assert not self.backend._is_safe_workspace(unsafe_workspace)
    
    def test_workspace_in_temp_dir_allowed(self):
        """Test workspace in temp directory is allowed."""
        import tempfile
        temp_workspace = Path(tempfile.gettempdir()) / "test_workspace_mg"
        temp_workspace.mkdir(exist_ok=True)
        try:
            assert self.backend._is_safe_workspace(temp_workspace)
        finally:
            temp_workspace.rmdir()
    
    def test_nonexistent_workspace_rejected(self):
        """Test non-existent workspace is rejected."""
        nonexistent = Path("/does/not/exist/workspace")
        
        assert not self.backend._is_safe_workspace(nonexistent)
    
    @pytest.mark.asyncio
    async def test_unsafe_workspace_blocks_render(self):
        """Test unsafe workspace blocks render operation."""
        unsafe_workspace = Path("/etc")  # System directory
        opts = RenderOpts(output_name="test.mp4", fps=30, quality="standard")
        
        result = await self.backend.render(unsafe_workspace, opts)
        
        assert not result.ok
        assert "Unsafe workspace path" in result.stderr