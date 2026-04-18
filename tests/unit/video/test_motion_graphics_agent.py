"""Unit tests for motion graphics agent factory."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from praisonai_tools.video.motion_graphics.agent import (
    create_motion_graphics_agent,
    RenderTools,
    _resolve_backend
)
from praisonai_tools.video.motion_graphics.protocols import RenderOpts, RenderResult, LintResult


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, instructions="", tools=None, llm="", **kwargs):
        self.instructions = instructions
        self.tools = tools or []
        self.llm = llm
        self.kwargs = kwargs


class MockFileTools:
    """Mock FileTools for testing."""
    
    def __init__(self, base_dir=""):
        self.base_dir = base_dir


class MockBackend:
    """Mock render backend for testing."""
    
    async def lint(self, workspace, strict=False):
        return LintResult(ok=True, messages=[])
    
    async def render(self, workspace, opts):
        output_name = getattr(opts, 'output_name', 'test.mp4')
        return RenderResult(
            ok=True,
            output_path=workspace / output_name,
            bytes_=b"test video data",
            size_kb=1024
        )


class TestRenderTools:
    """Test RenderTools class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.backend = MockBackend()
        self.workspace = Path("/tmp/test_workspace")
        self.render_tools = RenderTools(self.backend, self.workspace)
    
    @pytest.mark.asyncio
    async def test_lint_composition(self):
        """Test linting composition."""
        result = await self.render_tools.lint_composition(strict=True)
        
        assert result["ok"] is True
        assert result["messages"] == []
        assert "raw" in result
    
    @pytest.mark.asyncio
    async def test_render_composition(self):
        """Test rendering composition."""
        result = await self.render_tools.render_composition(
            output_name="custom.mp4",
            fps=60,
            quality="high"
        )
        
        assert result["ok"] is True
        assert "custom.mp4" in str(result["output_path"])
        assert result["size_kb"] == 1024
        assert result["bytes"] == b"test video data"
        assert result["stderr"] == ""


class TestResolveBackend:
    """Test backend resolution."""
    
    def test_resolve_string_backend(self):
        """Test resolving string backend specification."""
        backend = _resolve_backend("html")
        
        from praisonai_tools.video.motion_graphics.backend_html import HtmlRenderBackend
        assert isinstance(backend, HtmlRenderBackend)
    
    def test_resolve_unknown_backend(self):
        """Test resolving unknown backend raises error."""
        with pytest.raises(ValueError, match="Unknown backend"):
            _resolve_backend("unknown")
    
    def test_resolve_backend_instance(self):
        """Test resolving backend instance passes through."""
        mock_backend = MockBackend()
        result = _resolve_backend(mock_backend)
        
        assert result is mock_backend


class TestCreateMotionGraphicsAgent:
    """Test motion graphics agent factory."""
    
    @patch('praisonai_tools.video.motion_graphics.agent.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.agent.FileTools', MockFileTools)
    def test_create_agent_defaults(self):
        """Test creating agent with default parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = create_motion_graphics_agent(workspace=tmpdir)
            
            assert isinstance(agent, MockAgent)
            assert agent.llm == "claude-sonnet-4"
            assert len(agent.tools) == 2  # FileTools and RenderTools
            assert "motion graphics specialist" in agent.instructions.lower()
    
    @patch('praisonai_tools.video.motion_graphics.agent.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.agent.FileTools', MockFileTools)
    def test_create_agent_custom_params(self):
        """Test creating agent with custom parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = create_motion_graphics_agent(
                workspace=tmpdir,
                max_retries=5,
                llm="gpt-4",
                custom_param="test"
            )
            
            assert agent.llm == "gpt-4"
            assert "5" in agent.instructions  # max_retries mentioned
            assert agent.kwargs == {"custom_param": "test"}
    
    @patch('praisonai_tools.video.motion_graphics.agent.Agent', None)
    def test_create_agent_missing_praisonaiagents(self):
        """Test creating agent when praisonaiagents is not available."""
        with pytest.raises(ImportError, match="praisonaiagents not available"):
            create_motion_graphics_agent()
    
    @patch('praisonai_tools.video.motion_graphics.agent.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.agent.FileTools', MockFileTools)
    def test_create_agent_auto_workspace(self):
        """Test creating agent with automatic workspace creation."""
        agent = create_motion_graphics_agent()
        
        # Should create workspace automatically
        assert hasattr(agent, '_motion_graphics_workspace')
        assert agent._motion_graphics_workspace.exists()
    
    @patch('praisonai_tools.video.motion_graphics.agent.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.agent.FileTools', MockFileTools)
    def test_create_agent_custom_backend(self):
        """Test creating agent with custom backend."""
        mock_backend = MockBackend()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = create_motion_graphics_agent(
                workspace=tmpdir,
                backend=mock_backend
            )
            
            assert agent._motion_graphics_backend is mock_backend
    
    @patch('praisonai_tools.video.motion_graphics.agent.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.agent.FileTools', MockFileTools)
    def test_create_agent_workspace_creation(self):
        """Test agent creates workspace directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir) / "custom_workspace"
            
            agent = create_motion_graphics_agent(workspace=workspace_path)
            
            assert workspace_path.exists()
            assert agent._motion_graphics_workspace == workspace_path
    
    @patch('praisonai_tools.video.motion_graphics.agent.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.agent.FileTools', MockFileTools) 
    def test_create_agent_skill_included(self):
        """Test agent includes motion graphics skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = create_motion_graphics_agent(workspace=tmpdir)
            
            # Should include the skill content
            assert "GSAP" in agent.instructions
            assert "timeline" in agent.instructions
            assert "window.__timelines" in agent.instructions
    
    @patch('praisonai_tools.video.motion_graphics.agent.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.agent.FileTools', MockFileTools)
    def test_create_agent_output_validation(self):
        """Test agent includes output validation rules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = create_motion_graphics_agent(workspace=tmpdir, max_retries=3)
            
            # Should include strict output validation
            assert "CRITICAL OUTPUT VALIDATION" in agent.instructions
            assert "Never fabricate file paths" in agent.instructions
            assert "3 failed attempts" in agent.instructions
    
    @patch('praisonai_tools.video.motion_graphics.agent.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.agent.FileTools', MockFileTools)
    def test_agent_tools_configuration(self):
        """Test agent tools are configured correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = create_motion_graphics_agent(workspace=tmpdir)
            
            assert len(agent.tools) == 2
            
            # Check FileTools
            file_tools = agent.tools[0]
            assert isinstance(file_tools, MockFileTools)
            assert file_tools.base_dir == str(tmpdir)
            
            # Check RenderTools
            render_tools = agent.tools[1]
            assert isinstance(render_tools, RenderTools)
            assert render_tools.workspace == Path(tmpdir)