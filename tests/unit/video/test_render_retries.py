"""Tests for render retry functionality."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

try:
    from praisonai_tools.video.motion_graphics.agent import RenderTools
    from praisonai_tools.video.motion_graphics.protocols import RenderResult, RenderOpts
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False


class FailingBackend:
    """Mock backend that fails a specified number of times."""
    
    def __init__(self, max_fails: int = 999):
        self.max_fails = max_fails
        self.call_count = 0
    
    async def lint(self, workspace, strict=False):
        from praisonai_tools.video.motion_graphics.protocols import LintResult
        return LintResult(ok=True, messages=[], raw="")
    
    async def render(self, workspace, opts):
        self.call_count += 1
        
        if self.call_count <= self.max_fails:
            return RenderResult(
                ok=False,
                output_path=None,
                bytes_=None,
                stderr=f"Simulated failure {self.call_count}",
                size_kb=0
            )
        else:
            return RenderResult(
                ok=True,
                output_path=workspace / opts.output_name,
                bytes_=b"test video",
                stderr="",
                size_kb=1024
            )


@pytest.mark.skipif(not AGENT_AVAILABLE, reason="Motion graphics agent not available")
class TestRenderRetries:
    """Test bounded retry functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_render_composition_bounded_retries(self):
        """Test render_composition respects max_retries limit."""
        backend = FailingBackend(max_fails=999)  # Always fail
        tools = RenderTools(backend, self.temp_dir, max_retries=3)
        
        result = await tools.render_composition(output_name="test.mp4")
        
        assert backend.call_count == 3  # Should try exactly 3 times
        assert not result["ok"]
        assert "Simulated failure" in result["stderr"]
    
    @pytest.mark.asyncio
    async def test_render_composition_succeeds_after_retries(self):
        """Test render_composition succeeds after some failures."""
        backend = FailingBackend(max_fails=2)  # Fail twice, then succeed
        tools = RenderTools(backend, self.temp_dir, max_retries=3)
        
        result = await tools.render_composition(output_name="test.mp4")
        
        assert backend.call_count == 3  # Fail twice, succeed on third
        assert result["ok"]
        assert result["attempts"] == 3
    
    @pytest.mark.asyncio
    async def test_render_with_bounded_retries_integration(self):
        """Test render_with_bounded_retries with write/patch functions."""
        backend = FailingBackend(max_fails=1)  # Fail once, then succeed
        tools = RenderTools(backend, self.temp_dir, max_retries=2)
        
        write_calls = []
        patch_calls = []
        
        async def mock_write_fn(**kwargs):
            write_calls.append(kwargs)
        
        async def mock_patch_fn(error):
            patch_calls.append(error)
        
        result = await tools.render_with_bounded_retries(
            write_fn=mock_write_fn,
            patch_fn=mock_patch_fn,
            output_name="test.mp4"
        )
        
        assert len(write_calls) == 1  # write_fn called once initially
        assert len(patch_calls) == 1  # patch_fn called once for first failure
        assert result["ok"]  # Eventually succeeds