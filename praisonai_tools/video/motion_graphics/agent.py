"""Motion graphics agent factory."""

import tempfile
from pathlib import Path
from typing import Union, Any

try:
    from praisonaiagents import Agent
    from praisonaiagents.tools.file_tools import FileTools
except ImportError:
    # Fallback for development
    Agent = None
    FileTools = None

from .protocols import RenderBackendProtocol
from .backend_html import HtmlRenderBackend
from .skill import MOTION_GRAPHICS_SKILL


class RenderTools:
    """Tools for motion graphics rendering."""
    
    def __init__(self, backend: RenderBackendProtocol, workspace: Path, max_retries: int = 3):
        self.backend = backend
        self.workspace = workspace
        self.max_retries = max_retries
    
    async def lint_composition(self, strict: bool = False) -> dict:
        """Lint the motion graphics composition.
        
        Args:
            strict: Enable strict linting rules
            
        Returns:
            Dict with lint results
        """
        result = await self.backend.lint(self.workspace, strict)
        return {
            "ok": result.ok,
            "messages": result.messages,
            "raw": result.raw
        }
    
    async def render_composition(
        self,
        output_name: str = "video.mp4",
        fps: int = 30,
        quality: str = "standard"
    ) -> dict:
        """Render the motion graphics composition to MP4 with bounded retries.
        
        Args:
            output_name: Output filename
            fps: Frames per second
            quality: Quality setting (draft/standard/high)
            
        Returns:
            Dict with render results
        """
        from .protocols import RenderOpts
        
        opts = RenderOpts(
            output_name=output_name,
            fps=fps,
            quality=quality
        )
        
        # Direct render with bounded retries for transient failures
        # Note: For composition authoring retries, the agent should use render_iterate 
        # with appropriate write/lint/patch functions
        result = await self.backend.render(self.workspace, opts)
        attempts = 1
        
        while not result.ok and attempts < self.max_retries:
            # Retry for transient failures (e.g., ffmpeg timeouts)
            result = await self.backend.render(self.workspace, opts)
            attempts += 1
        
        return {
            "ok": result.ok,
            "output_path": str(result.output_path) if result.output_path else None,
            "size_kb": result.size_kb,
            "stderr": result.stderr,
            "attempts": attempts,
            "bytes": result.bytes_
        }
    
    async def render_with_bounded_retries(
        self,
        write_fn,
        patch_fn,
        output_name: str = "video.mp4", 
        fps: int = 30,
        quality: str = "standard",
        **kwargs
    ) -> dict:
        """Use render_iterate for full composition authoring with retries.
        
        Args:
            write_fn: Function to write initial composition
            patch_fn: Function to patch composition based on error
            output_name: Output filename
            fps: Frames per second  
            quality: Quality setting
            **kwargs: Arguments passed to write_fn
            
        Returns:
            Dict with render results
        """
        from ._render_loop import render_iterate
        from .protocols import RenderOpts
        
        opts = RenderOpts(output_name=output_name, fps=fps, quality=quality)
        
        async def lint_fn():
            return await self.backend.lint(self.workspace, strict=False)
            
        async def render_fn():
            return await self.backend.render(self.workspace, opts)
        
        result = await render_iterate(
            write_fn=write_fn,
            lint_fn=lint_fn,
            render_fn=render_fn,
            patch_fn=patch_fn,
            max_retries=self.max_retries,
            **kwargs
        )
        
        return {
            "ok": result.ok,
            "output_path": str(result.output_path) if result.output_path else None,
            "size_kb": result.size_kb,
            "stderr": result.stderr,
            "bytes": result.bytes_
        }


def create_motion_graphics_agent(
    *,
    backend: Union[RenderBackendProtocol, str] = "html",
    workspace: Union[str, Path] = None,
    max_retries: int = 3,
    llm: str = "claude-sonnet-4",
    **agent_kwargs: Any
) -> Any:
    """Create a motion graphics agent.
    
    Args:
        backend: Render backend or backend name
        workspace: Workspace directory for compositions
        max_retries: Maximum render retry attempts
        llm: LLM model to use
        **agent_kwargs: Additional arguments for Agent constructor
        
    Returns:
        Agent configured for motion graphics authoring
    """
    if Agent is None:
        raise ImportError(
            "praisonaiagents not available. Install with: pip install praisonaiagents"
        )
    
    # Set up workspace
    if workspace is None:
        workspace = Path(tempfile.mkdtemp(prefix="motion_graphics_"))
    else:
        workspace = Path(workspace)
    
    workspace.mkdir(parents=True, exist_ok=True)
    
    # Resolve backend
    render_backend = _resolve_backend(backend)
    
    # Base instructions for motion graphics authoring
    base_instructions = f"""
You are a motion graphics specialist agent. Your role is to create HTML/CSS/GSAP 
compositions that render to high-quality MP4 videos.

Key responsibilities:
1. Author HTML files with GSAP animations based on user prompts
2. Follow the motion graphics authoring skill guide precisely
3. Test compositions with lint and render tools
4. Iterate on failures with a maximum of {max_retries} attempts
5. Return concrete file paths and render status

CRITICAL OUTPUT VALIDATION:
- A render succeeded ONLY IF the output contains a concrete file path AND no error indicators
- Never fabricate file paths
- Always surface actual errors from the render backend
- Stop after {max_retries} failed attempts

Workspace directory: {workspace}
"""
    
    # Create tools.
    # FileTools is a utility class with bound methods; pass the instance so the
    # Agent can register read_file/write_file/list_files as callable tools.
    file_tools = FileTools()
    render_tools = RenderTools(render_backend, workspace, max_retries)
    
    # Create agent
    agent = Agent(
        instructions=base_instructions + "\n\n" + MOTION_GRAPHICS_SKILL,
        tools=[file_tools, render_tools],
        llm=llm,
        **agent_kwargs
    )
    
    # Store additional attributes
    agent._motion_graphics_backend = render_backend
    agent._motion_graphics_workspace = workspace
    agent._motion_graphics_max_retries = max_retries
    
    return agent


def _resolve_backend(backend: Union[RenderBackendProtocol, str]) -> RenderBackendProtocol:
    """Resolve backend specification to backend instance."""
    if isinstance(backend, str):
        if backend == "html":
            return HtmlRenderBackend()
        else:
            raise ValueError(f"Unknown backend: {backend}")
    
    return backend