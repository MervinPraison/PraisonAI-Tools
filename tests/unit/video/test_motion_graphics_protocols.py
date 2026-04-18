"""Unit tests for motion graphics protocols."""

import pytest
from pathlib import Path
from praisonai_tools.video.motion_graphics.protocols import (
    RenderOpts,
    LintResult, 
    RenderResult,
    RenderBackendProtocol
)


class TestRenderOpts:
    """Test RenderOpts dataclass."""
    
    def test_default_values(self):
        """Test default values are set correctly."""
        opts = RenderOpts()
        
        assert opts.output_name == "video.mp4"
        assert opts.fps == 30
        assert opts.quality == "standard"
        assert opts.format == "mp4"
        assert opts.strict is False
        assert opts.timeout == 300
    
    def test_custom_values(self):
        """Test custom values are set correctly."""
        opts = RenderOpts(
            output_name="custom.webm",
            fps=60,
            quality="high",
            format="webm",
            strict=True,
            timeout=600
        )
        
        assert opts.output_name == "custom.webm"
        assert opts.fps == 60
        assert opts.quality == "high"
        assert opts.format == "webm"
        assert opts.strict is True
        assert opts.timeout == 600


class TestLintResult:
    """Test LintResult dataclass."""
    
    def test_success_result(self):
        """Test successful lint result."""
        result = LintResult(ok=True, messages=[])
        
        assert result.ok is True
        assert result.messages == []
        assert result.raw == ""
    
    def test_failure_result(self):
        """Test failed lint result."""
        messages = ["Error 1", "Error 2"]
        raw_content = "<html>test</html>"
        
        result = LintResult(
            ok=False,
            messages=messages,
            raw=raw_content
        )
        
        assert result.ok is False
        assert result.messages == messages
        assert result.raw == raw_content


class TestRenderResult:
    """Test RenderResult dataclass."""
    
    def test_success_result(self):
        """Test successful render result."""
        output_path = Path("/tmp/video.mp4")
        video_bytes = b"fake video data"
        
        result = RenderResult(
            ok=True,
            output_path=output_path,
            bytes_=video_bytes,
            size_kb=1024
        )
        
        assert result.ok is True
        assert result.output_path == output_path
        assert result.bytes_ == video_bytes
        assert result.stderr == ""
        assert result.size_kb == 1024
    
    def test_failure_result(self):
        """Test failed render result."""
        stderr = "Render failed: invalid timeline"
        
        result = RenderResult(
            ok=False,
            output_path=None,
            bytes_=None,
            stderr=stderr
        )
        
        assert result.ok is False
        assert result.output_path is None
        assert result.bytes_ is None
        assert result.stderr == stderr
        assert result.size_kb == 0


class TestRenderBackendProtocol:
    """Test RenderBackendProtocol protocol."""
    
    def test_protocol_runtime_checkable(self):
        """Test that protocol is runtime checkable."""
        from praisonai_tools.video.motion_graphics.backend_html import HtmlRenderBackend
        
        backend = HtmlRenderBackend()
        assert isinstance(backend, RenderBackendProtocol)
    
    def test_protocol_methods_exist(self):
        """Test that protocol methods are properly defined."""
        # This should not raise an error if protocol is properly defined
        assert hasattr(RenderBackendProtocol, 'lint')
        assert hasattr(RenderBackendProtocol, 'render')


class MockRenderBackend:
    """Mock render backend for testing."""
    
    def __init__(self, lint_result=None, render_result=None):
        self.lint_result = lint_result or LintResult(ok=True, messages=[])
        self.render_result = render_result or RenderResult(
            ok=True, 
            output_path=Path("/tmp/test.mp4"),
            bytes_=b"test",
            size_kb=1
        )
        self.lint_calls = []
        self.render_calls = []
    
    async def lint(self, workspace: Path, strict: bool = False) -> LintResult:
        """Mock lint implementation."""
        self.lint_calls.append((workspace, strict))
        return self.lint_result
    
    async def render(self, workspace: Path, opts: RenderOpts) -> RenderResult:
        """Mock render implementation."""
        self.render_calls.append((workspace, opts))
        return self.render_result


class TestMockRenderBackend:
    """Test mock render backend."""
    
    def test_mock_backend_protocol_compliance(self):
        """Test that mock backend implements protocol."""
        backend = MockRenderBackend()
        assert isinstance(backend, RenderBackendProtocol)
    
    @pytest.mark.asyncio
    async def test_mock_backend_lint(self):
        """Test mock backend lint method."""
        lint_result = LintResult(ok=False, messages=["test error"])
        backend = MockRenderBackend(lint_result=lint_result)
        
        workspace = Path("/tmp/test")
        result = await backend.lint(workspace, strict=True)
        
        assert result == lint_result
        assert backend.lint_calls == [(workspace, True)]
    
    @pytest.mark.asyncio
    async def test_mock_backend_render(self):
        """Test mock backend render method."""
        render_result = RenderResult(
            ok=False,
            output_path=None, 
            bytes_=None,
            stderr="test error"
        )
        backend = MockRenderBackend(render_result=render_result)
        
        workspace = Path("/tmp/test")
        opts = RenderOpts(output_name="test.mp4")
        result = await backend.render(workspace, opts)
        
        assert result == render_result
        assert backend.render_calls == [(workspace, opts)]