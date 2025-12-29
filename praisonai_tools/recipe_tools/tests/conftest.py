"""Pytest configuration and fixtures for recipe tools tests."""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def fixtures_dir():
    """Get the fixtures directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_csv(fixtures_dir):
    """Get path to sample CSV file."""
    return fixtures_dir / "sample.csv"


@pytest.fixture
def sample_json(fixtures_dir):
    """Get path to sample JSON file."""
    return fixtures_dir / "sample.json"


@pytest.fixture
def sample_pdf(fixtures_dir):
    """Get path to sample PDF file."""
    return fixtures_dir / "sample.pdf"


@pytest.fixture
def sample_image(fixtures_dir):
    """Get path to sample image file."""
    return fixtures_dir / "sample.png"


@pytest.fixture
def sample_audio(fixtures_dir):
    """Get path to sample audio file."""
    return fixtures_dir / "sample.wav"


@pytest.fixture
def sample_video(fixtures_dir):
    """Get path to sample video file."""
    return fixtures_dir / "sample.mp4"


@pytest.fixture
def sample_repo(fixtures_dir):
    """Get path to sample git repository."""
    return fixtures_dir / "sample_repo"


@pytest.fixture
def sample_folder(fixtures_dir):
    """Get path to sample folder for archiving."""
    return fixtures_dir / "sample_folder"


@pytest.fixture
def has_ffmpeg():
    """Check if ffmpeg is available."""
    import shutil
    return shutil.which("ffmpeg") is not None


@pytest.fixture
def has_poppler():
    """Check if poppler tools are available."""
    import shutil
    return shutil.which("pdftotext") is not None


@pytest.fixture
def has_imagemagick():
    """Check if ImageMagick is available."""
    import shutil
    return shutil.which("convert") is not None


@pytest.fixture
def has_git():
    """Check if git is available."""
    import shutil
    return shutil.which("git") is not None


@pytest.fixture
def has_openai_key():
    """Check if OpenAI API key is available."""
    return bool(os.environ.get("OPENAI_API_KEY"))


# Markers
def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no external deps)")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "integration: Integration tests requiring API keys")
    config.addinivalue_line("markers", "requires_ffmpeg: Tests requiring ffmpeg")
    config.addinivalue_line("markers", "requires_poppler: Tests requiring poppler")
    config.addinivalue_line("markers", "requires_imagemagick: Tests requiring ImageMagick")
    config.addinivalue_line("markers", "requires_git: Tests requiring git")
    config.addinivalue_line("markers", "requires_openai: Tests requiring OpenAI API key")
