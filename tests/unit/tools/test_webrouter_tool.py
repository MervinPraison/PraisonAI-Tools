"""Offline tests for the optional WebRouter tool."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from praisonai_tools.tools.webrouter_tool import (
    WebRouterTool, webrouter_extract, webrouter_search,
)


@pytest.fixture
def backend():
    module = MagicMock()
    router = module.WebRouter.return_value.__enter__.return_value
    with patch.dict(sys.modules, {"web_router": module}):
        yield module, router


def test_search_maps_results_and_closes_client(backend):
    module, router = backend
    router.search.return_value.results = [
        SimpleNamespace(title="Python", url="https://python.org", content="Docs")
    ]
    result = WebRouterTool(provider="you-mcp").run(query="python", max_results=3)
    assert result == {"query": "python", "results": [
        {"title": "Python", "url": "https://python.org", "content": "Docs"}
    ]}
    router.search.assert_called_once_with("python", provider="you-mcp", max_results=3)
    module.WebRouter.return_value.__exit__.assert_called_once()


def test_extract_maps_documents_and_closes_client(backend):
    module, router = backend
    router.extract.return_value.documents = [
        SimpleNamespace(url="https://example.com", content="Example")
    ]
    result = WebRouterTool(extract_provider="jina").run(
        action="extract", url="https://example.com")
    assert result == {"documents": [{"url": "https://example.com", "content": "Example"}]}
    router.extract.assert_called_once_with("https://example.com", provider="jina")
    module.WebRouter.return_value.__exit__.assert_called_once()


@pytest.mark.parametrize("action,kwargs,message", [
    ("search", {}, "query is required"),
    ("extract", {}, "url is required"),
    ("unknown", {}, "Unknown action: unknown"),
])
def test_invalid_input_does_not_build_client(backend, action, kwargs, message):
    module, _ = backend
    assert WebRouterTool().run(action=action, **kwargs) == {"error": message}
    module.WebRouter.assert_not_called()


@pytest.mark.parametrize("method,arg", [("search", "python"), ("extract", "https://example.com")])
def test_optional_dependency_missing(method, arg):
    with patch.dict(sys.modules, {"web_router": None}):
        result = getattr(WebRouterTool(), method)(arg)
    assert "pip install 'webrouter>=0.16'" in result["error"]


@pytest.mark.parametrize("method,arg", [("search", "python"), ("extract", "https://example.com")])
def test_backend_failure_closes_client(backend, method, arg):
    module, router = backend
    getattr(router, method).side_effect = RuntimeError("unavailable")
    assert getattr(WebRouterTool(), method)(arg) == {"error": "unavailable"}
    module.WebRouter.return_value.__exit__.assert_called_once()


def test_empty_results(backend):
    _, router = backend
    router.search.return_value.results = []
    router.extract.return_value.documents = []
    assert webrouter_search("python") == {"query": "python", "results": []}
    assert webrouter_extract("https://example.com") == {"documents": []}


def test_package_discovery_and_helpers(backend):
    from praisonai_tools import WebRouterTool as discovered
    from praisonai_tools import get_tool_names, webrouter_search as search
    from praisonai_tools import webrouter_extract as extract

    assert discovered is WebRouterTool
    assert search is webrouter_search
    assert extract is webrouter_extract
    assert "WebRouterTool" in get_tool_names()
    _, router = backend
    router.search.return_value.results = []
    router.extract.return_value.documents = []
    search("python", max_results=2)
    extract("https://example.com")
    router.search.assert_called_once_with("python", provider="auto", max_results=2)
    router.extract.assert_called_once_with("https://example.com", provider="auto")
