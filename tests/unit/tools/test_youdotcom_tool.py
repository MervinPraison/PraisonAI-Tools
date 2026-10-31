"""Unit tests for You.com tools (no network, no API key required)."""

from unittest.mock import MagicMock, patch

from praisonai_tools.tools.youdotcom_tool import (
    YouTools,
    ydc,
    ydc_search,
    ydc_contents,
    ydc_news,
    ydc_images,
)


def test_missing_api_key_returns_error(monkeypatch):
    monkeypatch.delenv("YDC_API_KEY", raising=False)
    for fn, arg in (
        (ydc_search, "q"),
        (ydc_contents, "https://example.com"),
        (ydc_news, "q"),
        (ydc_images, "q"),
    ):
        result = fn(arg)
        assert "error" in result


def test_ydc_alias():
    assert ydc is ydc_search


def test_search_uses_client_and_returns_dict():
    response = MagicMock()
    response.model_dump.return_value = {"results": {"web": [], "news": []}}
    client = MagicMock()
    client.search.unified.return_value = response

    with patch.object(YouTools, "_get_client", return_value=(client, None)):
        result = YouTools().search("ai", count=3, freshness="week")

    assert result == {"results": {"web": [], "news": []}}
    kwargs = client.search.unified.call_args.kwargs
    assert kwargs["query"] == "ai"
    assert kwargs["count"] == 3
    assert kwargs["freshness"] == "week"


def test_search_exception_is_reported_as_error():
    client = MagicMock()
    client.search.unified.side_effect = RuntimeError("boom")

    with patch.object(YouTools, "_get_client", return_value=(client, None)):
        result = YouTools().search("ai")

    assert "boom" in result["error"]


def test_discovered_via_package():
    import praisonai_tools.tools as tools_pkg

    assert tools_pkg.YouTools is YouTools
    assert tools_pkg.ydc_search is ydc_search
