"""Contract tests for the focused Context.dev search/scrape integration."""

import json
import subprocess
import sys

import httpx
import pytest

from praisonai_tools import ContextTool, list_tools


@pytest.fixture
def calls(monkeypatch):
    """Capture requests without contacting Context.dev."""
    requests = []

    def post(url, **kwargs):
        requests.append({"url": url, **kwargs})
        return httpx.Response(
            200, json={"data": "result"}, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx, "post", post)
    return requests


def test_search_contract(calls):
    result = ContextTool(api_key="fixture-key").run(query="robotics", num_results=5)
    assert result == {"data": "result"}
    assert calls == [
        {
            "url": "https://api.context.dev/v1/web/search",
            "headers": {"Authorization": "Bearer fixture-key"},
            "json": {"query": "robotics", "numResults": 5},
            "timeout": 180.0,
            "follow_redirects": False,
        }
    ]


def test_scrape_contract(calls):
    result = ContextTool(api_key="fixture-key").run(
        action="scrape", url="https://example.com"
    )
    assert result == {"data": "result"}
    assert calls[0]["url"] == "https://api.context.dev/v1/web/scrape"
    assert calls[0]["json"] == {
        "url": "https://example.com",
        "formats": {"markdown": True},
    }
    assert calls[0]["follow_redirects"] is False


@pytest.mark.parametrize(
    "arguments",
    [
        {"action": "delete"},
        {"query": ""},
        {"query": "   "},
        {"query": None},
        {"query": "robotics", "num_results": 0},
        {"query": "robotics", "num_results": 101},
        {"query": "robotics", "num_results": True},
        {"query": "robotics", "num_results": 1.5},
        {"action": "scrape", "url": "file:///etc/passwd"},
        {"action": "scrape", "url": "https://"},
        {"action": "scrape", "url": "https://[invalid"},
        {"action": "scrape", "url": None},
    ],
)
def test_invalid_arguments_do_not_send_requests(calls, arguments):
    assert "error" in ContextTool(api_key="fixture-key").run(**arguments)
    assert not calls


@pytest.mark.parametrize("argument", ["actions", "options", "file_path", "api_base"])
def test_no_browser_actions_file_uploads_or_endpoint_overrides(calls, argument):
    with pytest.raises(TypeError):
        ContextTool(api_key="fixture-key").run(query="robotics", **{argument: "unused"})
    assert not calls


def test_missing_key_does_not_send_requests(monkeypatch, calls):
    monkeypatch.delenv("CONTEXT_DEV_API_KEY", raising=False)
    monkeypatch.delenv("CONTEXT_API_KEY", raising=False)
    assert "CONTEXT_DEV_API_KEY" in ContextTool().run(query="robotics")["error"]
    assert not calls


def test_key_precedence(monkeypatch, calls):
    monkeypatch.setenv("CONTEXT_DEV_API_KEY", "preferred-key")
    monkeypatch.setenv("CONTEXT_API_KEY", "legacy-key")
    assert ContextTool(api_key="explicit-key").api_key == "explicit-key"
    assert ContextTool().api_key == "preferred-key"
    monkeypatch.delenv("CONTEXT_DEV_API_KEY")
    assert ContextTool().api_key is None
    assert "error" in ContextTool().run(query="robotics")
    assert not calls


@pytest.mark.parametrize("status", [302, 401, 429, 500])
def test_http_errors_are_returned(monkeypatch, status):
    response = httpx.Response(
        status, request=httpx.Request("POST", "https://api.context.dev")
    )
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: response)
    result = ContextTool(api_key="fixture-key").run(query="robotics")
    assert "error" in result
    assert "fixture-key" not in result["error"]


def test_malformed_key_is_not_exposed_in_protocol_error(monkeypatch):
    key = "fixture-secret\n"

    def post(*args, **kwargs):
        header = kwargs["headers"]["Authorization"].encode()
        raise httpx.LocalProtocolError(f"Illegal header value {header!r}")

    monkeypatch.setattr(httpx, "post", post)
    result = ContextTool(api_key=key).run(query="robotics")
    assert result == {"error": "Context.dev request failed"}
    assert "fixture-secret" not in str(result)


def test_timeout_is_returned(monkeypatch):
    def post(*args, **kwargs):
        raise httpx.ReadTimeout("request timed out")

    monkeypatch.setattr(httpx, "post", post)
    assert ContextTool(api_key="fixture-key").run(query="robotics") == {
        "error": "Context.dev request failed",
    }


def test_invalid_json_is_returned(monkeypatch):
    response = httpx.Response(
        200, text="not json", request=httpx.Request("POST", "https://api.context.dev")
    )
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: response)
    assert ContextTool(api_key="fixture-key").run(query="robotics") == {
        "error": "Context.dev returned invalid JSON",
    }


def test_missing_optional_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "httpx", None)
    result = ContextTool(api_key="fixture-key").run(query="robotics")
    assert "praisonai-tools[context]" in result["error"]


def test_discovery_and_schema():
    from praisonai_tools.tools import ContextTool as exported

    assert exported is ContextTool
    entry = next(entry for entry in list_tools() if entry.name == "ContextTool")
    assert entry.extras == ("context",)
    tool = ContextTool()
    assert tool.validate()
    assert tool.validate_schema_roundtrip()
    properties = tool.get_schema()["function"]["parameters"]["properties"]
    assert properties["action"]["enum"] == ["search", "scrape"]
    assert set(properties) == {"action", "query", "url", "num_results"}


def test_import_does_not_load_httpx():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, json; from praisonai_tools import ContextTool; "
            "ContextTool(); print(json.dumps('httpx' in sys.modules))",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) is False
