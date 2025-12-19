"""Pytest configuration and fixtures for PraisonAI Tools tests."""

import os
import pytest


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "tavily: tests requiring TAVILY_API_KEY")
    config.addinivalue_line("markers", "exa: tests requiring EXA_API_KEY")
    config.addinivalue_line("markers", "youdotcom: tests requiring YDC_API_KEY")


@pytest.fixture
def tavily_api_key():
    """Get Tavily API key from environment."""
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        pytest.skip("TAVILY_API_KEY not set")
    return key


@pytest.fixture
def exa_api_key():
    """Get Exa API key from environment."""
    key = os.environ.get("EXA_API_KEY")
    if not key:
        pytest.skip("EXA_API_KEY not set")
    return key


@pytest.fixture
def ydc_api_key():
    """Get You.com API key from environment."""
    key = os.environ.get("YDC_API_KEY")
    if not key:
        pytest.skip("YDC_API_KEY not set")
    return key
