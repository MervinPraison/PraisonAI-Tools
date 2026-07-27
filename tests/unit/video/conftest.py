"""Pytest configuration for video/motion-graphics tests.

Most tests in this tree are fully mocked (protocols, dataclasses, mocked
backends) and run without the optional ``video-motion`` dependencies. Only a
subset actually constructs :class:`HtmlRenderBackend`, which hard-requires
``playwright`` and ``imageio-ffmpeg`` at construction time.

Rather than skipping the whole tree when those packages are absent (for example
a minimal ``pip install -e ".[dev]"`` where the wheels could not be resolved),
gate *only* the dependency-bound tests. Mark them with
``@pytest.mark.requires_video_deps`` and this hook skips just those when the
extras are missing, preserving coverage for the dependency-independent tests.
"""

import importlib.util

import pytest

_VIDEO_DEPS = ("playwright", "imageio_ffmpeg")
_MISSING_VIDEO_DEPS = [
    name for name in _VIDEO_DEPS if importlib.util.find_spec(name) is None
]
VIDEO_DEPS_AVAILABLE = not _MISSING_VIDEO_DEPS


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_video_deps: mark test as requiring the optional "
        "video-motion extras (playwright, imageio-ffmpeg).",
    )


def pytest_collection_modifyitems(config, items):
    if VIDEO_DEPS_AVAILABLE:
        return
    skip_reason = (
        "video-motion extra not installed "
        "(pip install -e '.[dev,video-motion]'); missing: "
        + ", ".join(_MISSING_VIDEO_DEPS)
    )
    skip_marker = pytest.mark.skip(reason=skip_reason)
    for item in items:
        if "requires_video_deps" in item.keywords:
            item.add_marker(skip_marker)
