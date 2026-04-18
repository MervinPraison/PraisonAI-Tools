"""Protocols and data structures for motion graphics rendering."""

from typing import Protocol, runtime_checkable, Literal
from dataclasses import dataclass
from pathlib import Path


Quality = Literal["draft", "standard", "high"]
Format = Literal["mp4", "webm", "mov"]


@dataclass
class RenderOpts:
    """Options for rendering motion graphics."""
    output_name: str = "video.mp4"
    fps: int = 30
    quality: Quality = "standard"
    format: Format = "mp4"
    strict: bool = False
    timeout: int = 300


@dataclass
class LintResult:
    """Result of linting motion graphics code."""
    ok: bool
    messages: list[str]
    raw: str = ""


@dataclass
class RenderResult:
    """Result of rendering motion graphics."""
    ok: bool
    output_path: Path | None
    bytes_: bytes | None
    stderr: str = ""
    size_kb: int = 0


@runtime_checkable
class RenderBackendProtocol(Protocol):
    """Protocol for motion graphics render backends.
    
    This protocol defines the interface for different rendering engines
    (HTML/GSAP, Manim, Remotion, etc.) to implement.
    """
    
    async def lint(self, workspace: Path, strict: bool = False) -> LintResult:
        """Lint the motion graphics code in the workspace.
        
        Args:
            workspace: Path to the workspace containing the motion graphics code
            strict: If True, enforce stricter linting rules
            
        Returns:
            LintResult with validation status and messages
        """
        ...
    
    async def render(self, workspace: Path, opts: RenderOpts) -> RenderResult:
        """Render motion graphics to video.
        
        Args:
            workspace: Path to the workspace containing the motion graphics code
            opts: Rendering options
            
        Returns:
            RenderResult with video bytes and metadata
        """
        ...