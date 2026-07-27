"""Pytest configuration for video/motion-graphics tests.

These tests exercise the HTML render backend which hard-requires the optional
``video-motion`` dependencies (``playwright`` and ``imageio-ffmpeg``) at
construction time. When those packages are absent (for example a minimal
``pip install -e ".[dev]"`` where the wheels could not be resolved), skip the
whole tree gracefully instead of surfacing ImportError failures.
"""

import pytest

pytest.importorskip(
    "playwright",
    reason="video-motion extra not installed (pip install -e '.[dev,video-motion]')",
)
pytest.importorskip(
    "imageio_ffmpeg",
    reason="video-motion extra not installed (pip install -e '.[dev,video-motion]')",
)
