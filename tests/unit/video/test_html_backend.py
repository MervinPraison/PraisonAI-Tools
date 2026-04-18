"""Unit tests for HTML render backend."""

import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from praisonai_tools.video.motion_graphics.backend_html import HtmlRenderBackend
from praisonai_tools.video.motion_graphics.protocols import RenderOpts, LintResult, RenderResult


class TestHtmlRenderBackend:
    """Test HTML render backend."""
    
    def test_import_error_handling(self):
        """Test that import errors are handled properly."""
        with patch('praisonai_tools.video.motion_graphics.backend_html.async_playwright', None):
            with pytest.raises(ImportError, match="Playwright not installed"):
                HtmlRenderBackend()
        
        with patch('praisonai_tools.video.motion_graphics.backend_html.imageio_ffmpeg', None):
            with pytest.raises(ImportError, match="imageio-ffmpeg not installed"):
                HtmlRenderBackend()
    
    def test_init_success(self):
        """Test successful initialization."""
        with patch('praisonai_tools.video.motion_graphics.backend_html.async_playwright', Mock()):
            with patch('praisonai_tools.video.motion_graphics.backend_html.imageio_ffmpeg', Mock()):
                backend = HtmlRenderBackend()
                assert backend is not None


class TestLinting:
    """Test linting functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('praisonai_tools.video.motion_graphics.backend_html.async_playwright', Mock()):
            with patch('praisonai_tools.video.motion_graphics.backend_html.imageio_ffmpeg', Mock()):
                self.backend = HtmlRenderBackend()
    
    @pytest.mark.asyncio
    async def test_lint_missing_index_html(self):
        """Test linting when index.html is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            result = await self.backend.lint(workspace)
            
            assert result.ok is False
            assert "index.html not found" in result.messages[0]
    
    @pytest.mark.asyncio
    async def test_lint_valid_composition(self):
        """Test linting valid composition."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create valid HTML
            html_content = """
            <!DOCTYPE html>
            <html>
            <head><script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script></head>
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
            
            result = await self.backend.lint(workspace)
            
            assert result.ok is True
            assert result.messages == []
    
    @pytest.mark.asyncio
    async def test_lint_missing_timeline_setup(self):
        """Test linting when timeline setup is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create HTML without timeline setup
            html_content = """
            <!DOCTYPE html>
            <html>
            <body><div id="stage"></div></body>
            </html>
            """
            (workspace / "index.html").write_text(html_content)
            
            result = await self.backend.lint(workspace)
            
            assert result.ok is False
            assert any("window.__timelines" in msg for msg in result.messages)
    
    @pytest.mark.asyncio 
    async def test_lint_missing_duration_attribute(self):
        """Test linting when duration attribute is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create HTML without duration attribute
            html_content = """
            <!DOCTYPE html>
            <html>
            <body>
                <div id="stage"></div>
                <script>window.__timelines = [];</script>
            </body>
            </html>
            """
            (workspace / "index.html").write_text(html_content)
            
            result = await self.backend.lint(workspace)
            
            assert result.ok is False
            assert any("data-duration" in msg for msg in result.messages)
    
    @pytest.mark.asyncio
    async def test_lint_problematic_patterns(self):
        """Test linting detects problematic patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create HTML with problematic patterns
            html_content = """
            <!DOCTYPE html>
            <html>
            <body>
                <div id="stage" data-duration="5.0"></div>
                <script>
                    const tl = gsap.timeline({ paused: true });
                    tl.to(".elem", { x: Math.random() * 100, repeat: -1 });
                    window.__timelines = [tl];
                </script>
            </body>
            </html>
            """
            (workspace / "index.html").write_text(html_content)
            
            result = await self.backend.lint(workspace)
            
            assert result.ok is False
            assert any("Math.random" in msg for msg in result.messages)
            assert any("repeat: -1" in msg for msg in result.messages)
    
    @pytest.mark.asyncio
    async def test_lint_strict_mode(self):
        """Test strict linting mode.""" 
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create HTML with visibility animation
            html_content = """
            <!DOCTYPE html>
            <html>
            <body>
                <div id="stage" data-duration="5.0"></div>
                <script>
                    const tl = gsap.timeline({ paused: true });
                    tl.to(".elem", { visibility: "hidden" });
                    window.__timelines = [tl];
                </script>
            </body>
            </html>
            """
            (workspace / "index.html").write_text(html_content)
            
            # Non-strict mode should pass
            result = await self.backend.lint(workspace, strict=False)
            assert not any("visibility" in msg for msg in result.messages)
            
            # Strict mode should fail
            result = await self.backend.lint(workspace, strict=True)
            assert any("visibility" in msg for msg in result.messages)
    
    @pytest.mark.asyncio
    async def test_lint_read_error(self):
        """Test linting when file cannot be read."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create empty file that can't be read as UTF-8
            (workspace / "index.html").write_bytes(b'\xff\xfe\x00\x00')
            
            result = await self.backend.lint(workspace)
            
            assert result.ok is False
            assert any("Failed to read" in msg for msg in result.messages)


class TestRendering:
    """Test rendering functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('praisonai_tools.video.motion_graphics.backend_html.async_playwright', Mock()):
            with patch('praisonai_tools.video.motion_graphics.backend_html.imageio_ffmpeg', Mock()):
                self.backend = HtmlRenderBackend()
    
    @pytest.mark.asyncio
    async def test_render_missing_index_html(self):
        """Test rendering when index.html is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            opts = RenderOpts()
            
            result = await self.backend.render(workspace, opts)
            
            assert result.ok is False
            assert "index.html not found" in result.stderr
    
    @pytest.mark.asyncio
    async def test_render_unsafe_workspace(self):
        """Test rendering with unsafe workspace path."""
        # Create a mock for _is_safe_workspace that returns False
        with patch.object(self.backend, '_is_safe_workspace', return_value=False):
            workspace = Path("/tmp/test")
            opts = RenderOpts()
            
            result = await self.backend.render(workspace, opts)
            
            assert result.ok is False
            assert "Unsafe workspace path" in result.stderr
    
    def test_is_safe_workspace(self):
        """Test workspace safety validation."""
        # Valid workspace
        valid_workspace = Path("/tmp/test_workspace")
        assert self.backend._is_safe_workspace(valid_workspace) is True
        
        # Test with actual path that exists
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            assert self.backend._is_safe_workspace(workspace) is True
    
    def test_get_crf_for_quality(self):
        """Test CRF value mapping for quality settings."""
        assert self.backend._get_crf_for_quality("draft") == "28"
        assert self.backend._get_crf_for_quality("standard") == "23"
        assert self.backend._get_crf_for_quality("high") == "18"
        assert self.backend._get_crf_for_quality("unknown") == "23"  # default
    
    @patch('shutil.which')
    @patch('praisonai_tools.video.motion_graphics.backend_html.imageio_ffmpeg')
    def test_get_ffmpeg_path(self, mock_imageio, mock_which):
        """Test FFmpeg path resolution."""
        # Test imageio-ffmpeg path
        mock_imageio.get_ffmpeg_exe.return_value = "/usr/local/bin/ffmpeg"
        result = self.backend._get_ffmpeg_path()
        assert result == "/usr/local/bin/ffmpeg"
        
        # Test system FFmpeg fallback
        mock_imageio.get_ffmpeg_exe.side_effect = Exception("Not found")
        mock_which.return_value = "/usr/bin/ffmpeg"
        result = self.backend._get_ffmpeg_path()
        assert result == "/usr/bin/ffmpeg"
        
        # Test FFmpeg not found
        mock_which.return_value = None
        with pytest.raises(FileNotFoundError, match="FFmpeg not found"):
            self.backend._get_ffmpeg_path()
    
    @pytest.mark.asyncio
    async def test_handle_network_request_gsap_allowed(self):
        """Test that GSAP CDN requests are allowed."""
        mock_route = AsyncMock()
        mock_request = Mock()
        mock_request.url = "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"
        
        await self.backend._handle_network_request(mock_route, mock_request)
        
        mock_route.continue_.assert_called_once()
        mock_route.abort.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_network_request_local_files_allowed(self):
        """Test that local file requests are allowed."""
        mock_route = AsyncMock()
        mock_request = Mock()
        mock_request.url = "file:///tmp/test/index.html"
        
        await self.backend._handle_network_request(mock_route, mock_request)
        
        mock_route.continue_.assert_called_once()
        mock_route.abort.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_network_request_blocked(self):
        """Test that other requests are blocked."""
        mock_route = AsyncMock()
        mock_request = Mock()
        mock_request.url = "https://malicious.com/script.js"
        
        await self.backend._handle_network_request(mock_route, mock_request)
        
        mock_route.continue_.assert_not_called()
        mock_route.abort.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_encode_frames_no_frames(self):
        """Test encoding with no frames raises error."""
        opts = RenderOpts()
        output_path = Path("/tmp/test.mp4")
        
        with pytest.raises(ValueError, match="No frames to encode"):
            await self.backend._encode_frames_to_mp4([], output_path, opts)
    
    @pytest.mark.asyncio 
    @patch('asyncio.create_subprocess_exec')
    async def test_encode_frames_success(self, mock_subprocess):
        """Test successful frame encoding."""
        # Setup mock subprocess
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"stdout", b"stderr")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process
        
        with patch.object(self.backend, '_get_ffmpeg_path', return_value='ffmpeg'):
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create fake frame files
                frame_dir = Path(tmpdir)
                frame_paths = []
                for i in range(3):
                    frame_path = frame_dir / f"frame_{i:06d}.png" 
                    frame_path.write_bytes(b"fake png data")
                    frame_paths.append(frame_path)
                
                opts = RenderOpts(fps=30, quality="standard", timeout=300)
                output_path = Path(tmpdir) / "test.mp4"
                
                await self.backend._encode_frames_to_mp4(frame_paths, output_path, opts)
                
                # Verify subprocess was called correctly
                mock_subprocess.assert_called_once()
                call_args = mock_subprocess.call_args[0]
                
                assert call_args[0] == 'ffmpeg'
                assert '-y' in call_args
                assert '-framerate' in call_args 
                assert '30' in call_args
                assert '-crf' in call_args
                assert '23' in call_args  # standard quality
    
    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_encode_frames_ffmpeg_failure(self, mock_subprocess):
        """Test FFmpeg failure handling."""
        # Setup mock subprocess that fails
        mock_process = AsyncMock() 
        mock_process.communicate.return_value = (b"stdout", b"encoding failed")
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process
        
        with patch.object(self.backend, '_get_ffmpeg_path', return_value='ffmpeg'):
            with tempfile.TemporaryDirectory() as tmpdir:
                frame_path = Path(tmpdir) / "frame_000000.png"
                frame_path.write_bytes(b"fake")
                
                opts = RenderOpts()
                output_path = Path(tmpdir) / "test.mp4"
                
                with pytest.raises(RuntimeError, match="FFmpeg failed"):
                    await self.backend._encode_frames_to_mp4([frame_path], output_path, opts)
    
    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_encode_frames_timeout(self, mock_subprocess):
        """Test FFmpeg timeout handling.""" 
        # Setup mock subprocess that times out
        mock_process = AsyncMock()
        mock_process.communicate.side_effect = asyncio.TimeoutError()
        mock_process.kill = Mock()
        mock_subprocess.return_value = mock_process
        
        with patch.object(self.backend, '_get_ffmpeg_path', return_value='ffmpeg'):
            with tempfile.TemporaryDirectory() as tmpdir:
                frame_path = Path(tmpdir) / "frame_000000.png"
                frame_path.write_bytes(b"fake")
                
                opts = RenderOpts(timeout=1)  # Short timeout
                output_path = Path(tmpdir) / "test.mp4"
                
                with pytest.raises(RuntimeError, match="FFmpeg encoding timed out"):
                    await self.backend._encode_frames_to_mp4([frame_path], output_path, opts)