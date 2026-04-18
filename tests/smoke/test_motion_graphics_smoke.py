"""Smoke tests for motion graphics module."""

import pytest
import tempfile
from pathlib import Path

# Skip tests if dependencies not available
playwright_available = True
try:
    import playwright
except ImportError:
    playwright_available = False

imageio_ffmpeg_available = True
try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg_available = False


class TestMotionGraphicsImports:
    """Test basic imports work."""
    
    def test_import_protocols(self):
        """Test importing protocols."""
        from praisonai_tools.video.motion_graphics import (
            RenderBackendProtocol,
            RenderOpts,
            RenderResult,
            LintResult
        )
        
        assert RenderBackendProtocol is not None
        assert RenderOpts is not None
        assert RenderResult is not None
        assert LintResult is not None
    
    def test_import_backend(self):
        """Test importing HTML backend."""
        if not playwright_available or not imageio_ffmpeg_available:
            pytest.skip("Playwright or imageio-ffmpeg not available")
        
        from praisonai_tools.video.motion_graphics import HtmlRenderBackend
        
        assert HtmlRenderBackend is not None
    
    def test_import_agent_factory(self):
        """Test importing agent factory."""
        from praisonai_tools.video.motion_graphics import create_motion_graphics_agent
        
        assert create_motion_graphics_agent is not None
    
    def test_import_team_preset(self):
        """Test importing team preset."""
        from praisonai_tools.video.motion_graphics import motion_graphics_team
        
        assert motion_graphics_team is not None
    
    def test_import_git_tools(self):
        """Test importing GitTools."""
        from praisonai_tools.tools.git_tools import GitTools
        
        assert GitTools is not None


class TestProtocolsBasic:
    """Test protocols work at basic level."""
    
    def test_render_opts_creation(self):
        """Test RenderOpts can be created."""
        from praisonai_tools.video.motion_graphics import RenderOpts
        
        opts = RenderOpts()
        assert opts.output_name == "video.mp4"
        assert opts.fps == 30
        
        custom_opts = RenderOpts(output_name="custom.mp4", fps=60)
        assert custom_opts.output_name == "custom.mp4"
        assert custom_opts.fps == 60
    
    def test_lint_result_creation(self):
        """Test LintResult can be created."""
        from praisonai_tools.video.motion_graphics import LintResult
        
        result = LintResult(ok=True, messages=[])
        assert result.ok is True
        assert result.messages == []
    
    def test_render_result_creation(self):
        """Test RenderResult can be created."""
        from praisonai_tools.video.motion_graphics import RenderResult
        
        result = RenderResult(
            ok=True,
            output_path=Path("/tmp/test.mp4"),
            bytes_=b"test",
            size_kb=1
        )
        assert result.ok is True
        assert result.output_path == Path("/tmp/test.mp4")


class TestHtmlBackendBasic:
    """Test HTML backend basic functionality."""
    
    @pytest.mark.skipif(
        not playwright_available or not imageio_ffmpeg_available,
        reason="Playwright or imageio-ffmpeg not available"
    )
    def test_backend_creation(self):
        """Test HTML backend can be created."""
        from praisonai_tools.video.motion_graphics import HtmlRenderBackend
        
        backend = HtmlRenderBackend()
        assert backend is not None
    
    @pytest.mark.skipif(
        not playwright_available or not imageio_ffmpeg_available,
        reason="Playwright or imageio-ffmpeg not available"
    )
    @pytest.mark.asyncio
    async def test_backend_lint_basic(self):
        """Test backend linting works at basic level."""
        from praisonai_tools.video.motion_graphics import HtmlRenderBackend
        
        backend = HtmlRenderBackend()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Test missing index.html
            result = await backend.lint(workspace)
            assert result.ok is False
            assert "index.html not found" in result.messages[0]
            
            # Test with valid HTML
            html_content = """
            <!DOCTYPE html>
            <html>
            <body>
                <div id="stage" data-duration="5.0"></div>
                <script>
                    const tl = gsap.timeline({ paused: true });
                    window.__timelines = [tl];
                </script>
            </body>
            </html>
            """
            (workspace / "index.html").write_text(html_content)
            
            result = await backend.lint(workspace)
            assert result.ok is True


class TestGitToolsBasic:
    """Test GitTools basic functionality."""
    
    def test_git_tools_creation(self):
        """Test GitTools can be created."""
        from praisonai_tools.tools.git_tools import GitTools
        
        with tempfile.TemporaryDirectory() as tmpdir:
            git_tools = GitTools(base_dir=tmpdir)
            assert git_tools.base_dir == Path(tmpdir)
    
    def test_git_tools_parse_repo(self):
        """Test repository parsing."""
        from praisonai_tools.tools.git_tools import GitTools
        
        git_tools = GitTools()
        
        # Test owner/repo format
        url, name = git_tools._parse_repo_input("owner/repo")
        assert "github.com/owner/repo" in url
        assert name == "owner_repo"
        
        # Test HTTPS URL
        url, name = git_tools._parse_repo_input("https://github.com/owner/repo.git")
        assert url == "https://github.com/owner/repo.git"
        assert name == "owner_repo"
    
    def test_git_tools_safety(self):
        """Test path safety features."""
        from praisonai_tools.tools.git_tools import GitTools
        
        git_tools = GitTools()
        
        # Test safe file paths
        assert git_tools._validate_file_path("README.md") == "README.md"
        assert git_tools._validate_file_path("src/main.py") == "src/main.py"
        
        # Test unsafe file paths
        with pytest.raises(ValueError):
            git_tools._validate_file_path("../etc/passwd")
        
        with pytest.raises(ValueError):
            git_tools._validate_file_path("../../secret.txt")


class TestEndToEndBasic:
    """Test basic end-to-end functionality."""
    
    def test_lazy_imports_work(self):
        """Test that lazy imports work correctly."""
        # This should not fail even if optional dependencies are missing
        import praisonai_tools.video.motion_graphics
        
        # Test accessing attributes triggers lazy loading
        try:
            _ = praisonai_tools.video.motion_graphics.RenderOpts
            protocols_available = True
        except ImportError:
            protocols_available = False
        
        # Protocols should always be available
        assert protocols_available
    
    def test_package_structure(self):
        """Test package structure is correct."""
        from praisonai_tools.video import motion_graphics
        
        # Check __all__ is defined
        assert hasattr(motion_graphics, '__all__')
        assert len(motion_graphics.__all__) > 0
        
        # Check key exports are listed
        assert 'RenderBackendProtocol' in motion_graphics.__all__
        assert 'RenderOpts' in motion_graphics.__all__
        assert 'create_motion_graphics_agent' in motion_graphics.__all__
        assert 'motion_graphics_team' in motion_graphics.__all__
    
    @pytest.mark.skipif(
        not playwright_available or not imageio_ffmpeg_available,
        reason="Playwright or imageio-ffmpeg not available"
    )
    def test_backend_protocol_compliance(self):
        """Test backend implements protocol correctly."""
        from praisonai_tools.video.motion_graphics import (
            HtmlRenderBackend,
            RenderBackendProtocol
        )
        
        backend = HtmlRenderBackend()
        assert isinstance(backend, RenderBackendProtocol)
    
    def test_agent_factory_imports(self):
        """Test agent factory can be imported."""
        from praisonai_tools.video.motion_graphics.agent import (
            create_motion_graphics_agent,
            RenderTools,
            _resolve_backend
        )
        
        assert create_motion_graphics_agent is not None
        assert RenderTools is not None
        assert _resolve_backend is not None
    
    def test_team_preset_imports(self):
        """Test team preset can be imported."""
        from praisonai_tools.video.motion_graphics.team import motion_graphics_team
        
        assert motion_graphics_team is not None


class TestSkillContent:
    """Test skill content is valid."""
    
    def test_skill_import(self):
        """Test skill can be imported."""
        from praisonai_tools.video.motion_graphics.skill import MOTION_GRAPHICS_SKILL
        
        assert MOTION_GRAPHICS_SKILL is not None
        assert len(MOTION_GRAPHICS_SKILL) > 1000  # Should be substantial
    
    def test_skill_content(self):
        """Test skill contains expected content."""
        from praisonai_tools.video.motion_graphics.skill import MOTION_GRAPHICS_SKILL
        
        skill = MOTION_GRAPHICS_SKILL.lower()
        
        # Should contain key concepts
        assert "gsap" in skill
        assert "timeline" in skill
        assert "window.__timelines" in skill
        assert "deterministic" in skill
        assert "data-duration" in skill
        assert "paused: true" in skill