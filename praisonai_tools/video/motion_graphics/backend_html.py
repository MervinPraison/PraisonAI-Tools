"""HTML/GSAP render backend using Playwright and FFmpeg."""

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

from .protocols import RenderBackendProtocol, RenderOpts, RenderResult, LintResult


class HtmlRenderBackend:
    """HTML/GSAP render backend using Playwright + FFmpeg.
    
    This backend:
    1. Runs Chromium headless to load HTML/GSAP compositions
    2. Drives GSAP timelines frame-by-frame via JavaScript
    3. Captures frames as images
    4. Encodes frames to MP4 using FFmpeg
    
    Security features:
    - Network requests blocked except allowlisted GSAP CDN
    - Workspace path validation to prevent escapes
    - Subprocess timeout limits
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        if async_playwright is None:
            raise ImportError(
                "Playwright not installed. Install with: pip install playwright"
            )
        if imageio_ffmpeg is None:
            raise ImportError(
                "imageio-ffmpeg not installed. Install with: pip install imageio-ffmpeg"
            )
        
        # Set allowed base directory for workspace safety
        if base_dir is None:
            # Default to current working directory and temp directory as allowed roots
            self._allowed_base = Path.cwd()
        else:
            self._allowed_base = Path(base_dir).resolve()
    
    async def lint(self, workspace: Path, strict: bool = False) -> LintResult:
        """Lint HTML composition for common issues."""
        index_html = workspace / "index.html"
        
        if not index_html.exists():
            return LintResult(
                ok=False,
                messages=["index.html not found in workspace"],
                raw=""
            )
        
        try:
            content = index_html.read_text(encoding="utf-8")
        except Exception as e:
            return LintResult(
                ok=False,
                messages=[f"Failed to read index.html: {e}"],
                raw=""
            )
        
        messages = []
        
        # Check for required GSAP timeline setup
        if "window.__timelines" not in content:
            messages.append("Missing window.__timelines setup")
        
        # Check for required data attributes
        if 'data-duration' not in content:
            messages.append("Missing data-duration attribute on timeline elements")
        
        # Check for problematic patterns
        if "Math.random" in content:
            messages.append("Math.random() detected - animations must be deterministic")
        
        if "repeat: -1" in content:
            messages.append("Infinite repeat detected (`repeat: -1`) — use finite repeat counts")
        
        if strict:
            # Additional strict checks
            if "visibility" in content or "display" in content:
                messages.append("Avoid animating visibility/display properties - use opacity instead")
        
        return LintResult(
            ok=len(messages) == 0,
            messages=messages,
            raw=content
        )
    
    async def render(self, workspace: Path, opts: RenderOpts) -> RenderResult:
        """Render HTML composition to MP4."""
        # Validate workspace path
        if not self._is_safe_workspace(workspace):
            return RenderResult(
                ok=False,
                output_path=None,
                bytes_=None,
                stderr="Unsafe workspace path"
            )
        
        # Check if index.html exists
        index_html = workspace / "index.html"
        if not index_html.exists():
            return RenderResult(
                ok=False,
                output_path=None,
                bytes_=None,
                stderr="index.html not found in workspace"
            )
        
        try:
            return await self._render_with_playwright(workspace, opts)
        except Exception as e:
            return RenderResult(
                ok=False,
                output_path=None,
                bytes_=None,
                stderr=str(e)
            )
    
    def _is_safe_workspace(self, workspace: Path) -> bool:
        """Check if workspace path is safe (prevents path traversal)."""
        try:
            workspace_abs = workspace.resolve(strict=True)
            allowed_base_abs = self._allowed_base.resolve()
            
            # Also allow temp directories
            temp_base = Path(tempfile.gettempdir()).resolve()
            
            # Check if workspace is under allowed base or temp directory
            try:
                # Check if workspace is relative to allowed base
                workspace_abs.relative_to(allowed_base_abs)
                return True
            except ValueError:
                pass
                
            try:
                # Check if workspace is relative to temp directory
                workspace_abs.relative_to(temp_base)
                return True
            except ValueError:
                pass
                
            return False
        except (OSError, ValueError):
            return False
    
    async def _render_with_playwright(self, workspace: Path, opts: RenderOpts) -> RenderResult:
        """Render using Playwright + FFmpeg."""
        output_path = workspace / opts.output_name
        
        async with async_playwright() as p:
            # Launch browser with security options
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding"
                ]
            )
            
            try:
                page = await browser.new_page(
                    viewport={"width": 1920, "height": 1080}
                )
                
                # Block network requests except allowlisted domains
                await page.route("**/*", self._handle_network_request)
                
                # Load the HTML file
                file_url = f"file://{workspace.absolute()}/index.html"
                await page.goto(file_url, wait_until="networkidle")
                
                # Wait for GSAP and timeline setup
                await page.wait_for_function("window.__timelines", timeout=10000)
                
                # Get timeline duration
                duration = await page.evaluate("""
                    () => {
                        const timelines = window.__timelines;
                        if (!timelines || timelines.length === 0) return 0;
                        return Math.max(...timelines.map(tl => tl.duration()));
                    }
                """)
                
                if duration <= 0:
                    raise ValueError("Invalid timeline duration")
                
                # Calculate frame count
                frame_count = int(duration * opts.fps)
                
                # Create temporary directory for frames
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    frame_paths = []
                    
                    # Capture frames
                    for frame in range(frame_count):
                        time = frame / opts.fps
                        
                        # Seek timeline to specific time
                        await page.evaluate(f"""
                            () => {{
                                const timelines = window.__timelines;
                                timelines.forEach(tl => {{
                                    tl.seek({time});
                                }});
                            }}
                        """)
                        
                        # Wait a bit for animations to settle
                        await page.wait_for_timeout(50)
                        
                        # Capture frame. Clip to the fixed 1920x1080 viewport —
                        # `full_page=True` can produce odd-height images when
                        # content overflows, which libx264 rejects (height must
                        # be divisible by 2).
                        frame_path = temp_path / f"frame_{frame:06d}.png"
                        await page.screenshot(
                            path=str(frame_path),
                            clip={"x": 0, "y": 0, "width": 1920, "height": 1080},
                        )
                        frame_paths.append(frame_path)
                    
                    # Encode to MP4 using FFmpeg
                    await self._encode_frames_to_mp4(
                        frame_paths, output_path, opts
                    )
                    
            finally:
                await browser.close()
        
        # Read video bytes
        video_bytes = None
        size_kb = 0
        if output_path.exists():
            video_bytes = output_path.read_bytes()
            size_kb = len(video_bytes) // 1024
        
        return RenderResult(
            ok=output_path.exists(),
            output_path=output_path if output_path.exists() else None,
            bytes_=video_bytes,
            stderr="",
            size_kb=size_kb
        )
    
    async def _handle_network_request(self, route, request):
        """Handle network requests with allowlist."""
        url = request.url
        
        # Allow GSAP CDN
        if "cdnjs.cloudflare.com" in url and "gsap" in url:
            await route.continue_()
            return
        
        # Allow local files
        if url.startswith("file://"):
            await route.continue_()
            return
        
        # Block everything else
        await route.abort()
    
    async def _encode_frames_to_mp4(
        self, 
        frame_paths: list[Path], 
        output_path: Path, 
        opts: RenderOpts
    ):
        """Encode frame sequence to MP4 using FFmpeg."""
        if not frame_paths:
            raise ValueError("No frames to encode")
        
        # Get FFmpeg path
        ffmpeg_path = self._get_ffmpeg_path()
        
        # Build FFmpeg command
        cmd = [
            ffmpeg_path,
            "-y",  # Overwrite output
            "-framerate", str(opts.fps),
            "-i", str(frame_paths[0].parent / "frame_%06d.png"),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", self._get_crf_for_quality(opts.quality),
            "-pix_fmt", "yuv420p",
            str(output_path)
        ]
        
        # Run FFmpeg
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=opts.timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            raise RuntimeError("FFmpeg encoding timed out")
        
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
    
    def _get_ffmpeg_path(self) -> str:
        """Get FFmpeg executable path."""
        # Try imageio-ffmpeg first
        if imageio_ffmpeg:
            try:
                return imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                pass
        
        # Fallback to system FFmpeg
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            return ffmpeg
        
        raise FileNotFoundError("FFmpeg not found")
    
    def _get_crf_for_quality(self, quality: str) -> str:
        """Get CRF value for quality setting."""
        quality_map = {
            "draft": "28",
            "standard": "23", 
            "high": "18"
        }
        return quality_map.get(quality, "23")