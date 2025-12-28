"""PraisonAI Video Tools - AI-powered video editing CLI and tools.

This module provides video editing capabilities including:
- Video probing (metadata extraction)
- Audio transcription with word-level timestamps
- LLM-based content analysis and edit planning
- FFmpeg-based video rendering

Usage:
    # As CLI
    python -m praisonai_tools.video edit input.mp4 --output edited.mp4
    python -m praisonai_tools.video probe input.mp4
    python -m praisonai_tools.video transcribe input.mp4 --output transcript.srt
    
    # As library
    from praisonai_tools.video import probe_video, transcribe_video, edit_video
"""

# Lazy imports to avoid dependency issues when running standalone
def __getattr__(name):
    """Lazy load video tools."""
    if name == "probe_video":
        from .probe import probe_video
        return probe_video
    elif name == "VideoProbeResult":
        from .probe import VideoProbeResult
        return VideoProbeResult
    elif name == "transcribe_video":
        from .transcribe import transcribe_video
        return transcribe_video
    elif name == "TranscriptResult":
        from .transcribe import TranscriptResult
        return TranscriptResult
    elif name == "create_edit_plan":
        from .plan import create_edit_plan
        return create_edit_plan
    elif name == "EditPlan":
        from .plan import EditPlan
        return EditPlan
    elif name == "render_video":
        from .render import render_video
        return render_video
    elif name == "edit_video":
        from .pipeline import edit_video
        return edit_video
    elif name == "VideoEditResult":
        from .pipeline import VideoEditResult
        return VideoEditResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "probe_video",
    "VideoProbeResult",
    "transcribe_video",
    "TranscriptResult",
    "create_edit_plan",
    "EditPlan",
    "render_video",
    "edit_video",
    "VideoEditResult",
]
