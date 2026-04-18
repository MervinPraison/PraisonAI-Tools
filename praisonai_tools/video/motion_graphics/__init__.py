"""Motion Graphics Video Pipeline for PraisonAI.

This module provides a programmatic motion-graphics video pipeline that can turn
natural-language prompts into short explainer MP4s without depending on paid
generative video APIs. The pipeline uses an agent-centric team approach where
a coordinator routes to specialists that research, read code, author HTML/CSS/JS
compositions with GSAP animations, and render to MP4 via a headless browser.

Usage:
    # Team preset
    from praisonai_tools.video.motion_graphics import motion_graphics_team
    
    team = motion_graphics_team()
    team.start("Animate Dijkstra's algorithm on a small weighted graph, 30s.")
    
    # Individual agent
    from praisonai_tools.video.motion_graphics import create_motion_graphics_agent
    
    agent = create_motion_graphics_agent()
    agent.start("Create an animation explaining the CAP theorem")
"""

# Lazy imports to avoid dependency issues when running standalone
def __getattr__(name):
    """Lazy load motion graphics tools."""
    if name == "RenderBackendProtocol":
        from .protocols import RenderBackendProtocol
        return RenderBackendProtocol
    elif name == "RenderOpts":
        from .protocols import RenderOpts
        return RenderOpts
    elif name == "RenderResult":
        from .protocols import RenderResult
        return RenderResult
    elif name == "LintResult":
        from .protocols import LintResult
        return LintResult
    elif name == "HtmlRenderBackend":
        from .backend_html import HtmlRenderBackend
        return HtmlRenderBackend
    elif name == "create_motion_graphics_agent":
        from .agent import create_motion_graphics_agent
        return create_motion_graphics_agent
    elif name == "motion_graphics_team":
        from .team import motion_graphics_team
        return motion_graphics_team
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "RenderBackendProtocol",
    "RenderOpts", 
    "RenderResult",
    "LintResult",
    "HtmlRenderBackend",
    "create_motion_graphics_agent",
    "motion_graphics_team",
]