import base64
import json

import pytest

from praisonai_tools import (
    ContextBatchToolkit,
    ContextBrandToolkit,
    ContextParse,
    ContextSearch,
    ContextScrape,
    ContextToolkit,
    ContextWebToolkit,
)
from praisonai_tools.tools.context_tool import ContextTool


EXPECTED_ENDPOINTS = {
    "parse-document",
    "web-scrape-html",
    "web-scrape-markdown",
    "web-scrape-images",
    "web-scrape-sitemap",
    "web-crawl",
    "web-extract",
    "web-search",
    "brand-retrieve-unified",
    "web-styleguide",
    "web-fonts",
    "web-screenshot",
    "web-naics",
    "web-sic",
    "list-monitors",
    "create-monitor",
    "get-monitor",
    "update-monitor",
    "delete-monitor",
    "list-monitor-runs",
    "list-monitor-changes",
    "list-account-runs",
    "list-monitor-credit-usage",
    "list-changes",
    "get-change",
    "run-monitor-now",
    "submit-batch",
    "list-batches",
    "get-batch",
    "delete-batch",
    "get-batch-results",
    "cancel-batch",
    "get-monitor-run",
}


class _Response:
    is_error = False
    status_code = 200
    text = ""

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class _Client:
    def __init__(self, payload=None):
        self.payload = payload or {"ok": True, "request_id": "hidden"}
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        return _Response(self.payload)


def test_complete_catalog_and_safe_defaults():
    safe_tools = ContextToolkit(api_key="test").get_tools()
    all_tools = ContextToolkit(
        api_key="test",
        include_write_tools=True,
        allow_browser_actions=True,
    ).get_tools()

    assert len(all_tools) == 33
    assert len(safe_tools) == 26
    assert len({tool.name for tool in all_tools}) == 33
    assert {tool.endpoint for tool in all_tools} == EXPECTED_ENDPOINTS
    assert "context_submit_batch" not in {tool.name for tool in safe_tools}
    assert "context_submit_batch" in {tool.name for tool in all_tools}


def test_tool_group_counts():
    assert len(ContextWebToolkit(api_key="test").get_tools()) == 9
    assert len(ContextBrandToolkit(api_key="test").get_tools()) == 5
    assert len(ContextBatchToolkit(api_key="test").get_tools()) == 3
    assert len(ContextBatchToolkit(api_key="test", include_write_tools=True).get_tools()) == 6


def test_every_schema_is_valid_and_described():
    for tool in ContextToolkit(api_key="test", include_write_tools=True).get_tools():
        assert tool.validate()
        assert tool.validate_schema_roundtrip()
        assert set(tool.annotations) == {"readOnlyHint", "destructiveHint", "openWorldHint"}
        assert all(isinstance(value, bool) for value in tool.annotations.values())
        for schema in tool.parameters["properties"].values():
            assert schema.get("description")


def test_search_request_shape_and_response_sanitizing():
    client = _Client({"results": [{"url": "https://context.dev"}], "request_id": "secret"})
    result = ContextSearch(api_key="test", client=client).run(
        query="Context.dev",
        numResults=10,
        includeDomains=["context.dev"],
    )

    assert result == {"results": [{"url": "https://context.dev"}]}
    request = client.calls[0]
    assert request["method"] == "POST"
    assert request["url"].endswith("/web/search")
    assert request["json"]["query"] == "Context.dev"
    assert request["headers"]["Authorization"] == "Bearer test"


def test_path_query_header_and_options_mapping():
    client = _Client()
    ContextTool("get-batch-results", api_key="test", client=client).run(
        batch_id="bat / one",
        limit=25,
        options={"cursor": "next"},
    )
    request = client.calls[0]
    assert request["url"].endswith("/batch/bat%20%2F%20one/results")
    assert dict(request["params"]) == {"limit": "25", "cursor": "next"}

    ContextTool("submit-batch", api_key="test", client=client).run(
        input={"type": "urls", "urls": ["https://example.com"]},
        **{"Idempotency-Key": "submission-1"},
    )
    request = client.calls[1]
    assert request["headers"]["Idempotency-Key"] == "submission-1"
    assert request["json"]["input"]["urls"] == ["https://example.com"]


def test_parse_accepts_base64_without_local_file_access():
    client = _Client({"markdown": "hello"})
    tool = ContextParse(api_key="test", client=client)

    assert "file_path" not in tool.parameters["properties"]
    assert tool.run(file_base64=base64.b64encode(b"world").decode()) == {"markdown": "hello"}
    assert client.calls[0]["content"] == b"world"


def test_parse_local_files_require_a_bounded_upload_directory(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    source = upload_dir / "hello.txt"
    source.write_text("hello")
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")
    client = _Client({"markdown": "hello"})

    with pytest.raises(ValueError, match="upload_dir"):
        ContextParse(api_key="test", client=client, allow_local_files=True)
    with pytest.raises(ValueError, match="Local file access is disabled"):
        ContextParse(api_key="test", client=client).run(file_path=str(source))

    tool = ContextParse(
        api_key="test",
        client=client,
        allow_local_files=True,
        upload_dir=upload_dir,
    )
    assert "file_path" in tool.parameters["properties"]
    assert tool.run(file_path=str(source), extension="txt") == {"markdown": "hello"}
    assert client.calls[0]["content"] == b"hello"
    assert dict(client.calls[0]["params"])["extension"] == "txt"
    with pytest.raises(ValueError, match="configured upload directory"):
        tool.run(file_path=str(outside))


def test_browser_actions_are_hidden_by_default():
    safe_scrape = next(
        tool for tool in ContextWebToolkit(api_key="test").get_tools()
        if tool.name == "context_web_scrape_markdown"
    )
    enabled_scrape = next(
        tool for tool in ContextWebToolkit(api_key="test", allow_browser_actions=True).get_tools()
        if tool.name == "context_web_scrape_markdown"
    )
    assert "actions" not in safe_scrape.parameters["properties"]
    assert "actions" in enabled_scrape.parameters["properties"]
    with pytest.raises(ValueError, match="Browser actions are disabled"):
        safe_scrape.run(url="https://example.com", options={"actions": [{"type": "click"}]})

    assert "actions" not in ContextScrape(api_key="test").parameters["properties"]
    assert "actions" not in ContextTool("web-scrape-markdown", api_key="test").parameters["properties"]


def test_configuration_and_input_errors_are_clear(monkeypatch):
    monkeypatch.delenv("CONTEXT_DEV_API_KEY", raising=False)
    monkeypatch.delenv("CONTEXT_API_KEY", raising=False)
    with pytest.raises(ValueError, match="CONTEXT_DEV_API_KEY"):
        ContextSearch(client=_Client()).run(query="test")
    with pytest.raises(ValueError, match="Missing required input: query"):
        ContextSearch(api_key="test", client=_Client()).run()
    with pytest.raises(ValueError, match="Duplicate values"):
        ContextSearch(api_key="test", client=_Client()).run(query="a", options={"query": "b"})


def test_catalog_is_json_serializable():
    schemas = [tool.get_schema() for tool in ContextToolkit(api_key="test", include_write_tools=True).get_tools()]
    assert len(json.loads(json.dumps(schemas))) == 33


def test_every_endpoint_builds_a_request():
    required_values = {
        "url": "https://example.com",
        "domain": "example.com",
        "query": "example",
        "schema": {"type": "object", "properties": {}},
        "body": {"type": "by_domain", "domain": "example.com"},
        "input": {"type": "urls", "urls": ["https://example.com"]},
        "name": "Example monitor",
        "target": {"type": "page", "url": "https://example.com"},
        "monitor_id": "mon_123",
        "change_id": "chg_123",
        "run_id": "run_123",
        "batch_id": "bat_123",
    }
    client = _Client()
    tools = ContextToolkit(
        api_key="test",
        client=client,
        include_write_tools=True,
        allow_browser_actions=True,
    ).get_tools()
    for tool in tools:
        kwargs = {field: required_values[field] for field in tool.parameters["required"]}
        if tool.endpoint == "parse-document":
            kwargs = {"file_base64": base64.b64encode(b"hello").decode()}
        assert tool.run(**kwargs) == {"ok": True}

    assert len(client.calls) == 33
    assert all(call["url"].startswith("https://api.context.dev/v1/") for call in client.calls)
