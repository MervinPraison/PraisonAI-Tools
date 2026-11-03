import json
import socket
from copy import deepcopy

import httpx
import pytest

from praisonai_tools import get_tool_names, list_tools
from praisonai_tools.tools.base import BaseTool, ToolResult


SOURCES = {
    "reddit_stocks": "/reddit/stocks/v1",
    "x_stocks": "/x/stocks/v1",
    "news_stocks": "/news/stocks/v1",
    "polymarket_stocks": "/polymarket/stocks/v1",
    "reddit_crypto": "/reddit/crypto/v1",
}
OPERATIONS = ["trending", "asset", "compare", "search", "market_sentiment"]
KEY = "test-only-private-key"


def test_discovery_advertises_adanos():
    assert "AdanosTool" in get_tool_names()


@pytest.fixture
def tool_class():
    from praisonai_tools import AdanosTool
    from praisonai_tools.tools import AdanosTool as DiscoveredTool

    assert AdanosTool is DiscoveredTool
    return AdanosTool


@pytest.fixture
def http(monkeypatch):
    real_client = httpx.Client
    state = {"requests": [], "clients": [], "closed": 0,
             "response": httpx.Response(200, json=[])}

    def handle(request):
        state["requests"].append(request)
        response = state["response"]
        if isinstance(response, Exception):
            raise response
        return response

    class Transport(httpx.MockTransport):
        def close(self):
            state["closed"] += 1
            super().close()

    def client(**kwargs):
        instance = real_client(transport=Transport(handle), **kwargs)
        state["clients"].append(instance)
        return instance

    monkeypatch.setattr(httpx, "Client", client)
    monkeypatch.delenv("ADANOS_API_KEY", raising=False)
    yield state
    assert all(client.is_closed for client in state["clients"])
    assert state["closed"] == len(state["clients"])


def payload(source, operation):
    crypto = source == "reddit_crypto"
    identity = {"symbol" if crypto else "ticker": "BTC" if crypto else "AAPL"}
    if operation == "asset":
        return {**identity, "found": False, "buzz_score": None,
                "sentiment_score": None, "period_days": 7}
    if operation == "compare":
        return {"period_days": 7, "tokens" if crypto else "stocks": []}
    if operation == "search":
        return {"query": "apple", "count": 0, "period_days": 7, "results": []}
    metrics = {"buzz_score": None, "active_tickers": 0,
               "positive_count": 0, "negative_count": 0, "neutral_count": 0,
               "bullish_pct": 0, "bearish_pct": 0, "trend_history": [], "drivers": []}
    if source == "polymarket_stocks":
        metrics.update(trade_count=0, market_count=0, current_market_count=0,
                       total_liquidity=0, unique_traders=None)
    else:
        metrics["mentions"] = 0
        if source == "news_stocks":
            metrics.update(unique_articles=0, source_count=0)
        elif source == "x_stocks":
            metrics.update(unique_tweets=0, unique_authors=0, total_upvotes=0)
        else:
            metrics.update(unique_posts=0, subreddit_count=0, total_upvotes=0)
    if operation == "market_sentiment":
        return metrics
    metrics.update(identity, buzz_score=0, trend="stable", sentiment_score=0)
    return [metrics]


@pytest.mark.parametrize("source", SOURCES)
@pytest.mark.parametrize("operation", OPERATIONS)
def test_all_native_requests(tool_class, http, source, operation):
    data = payload(source, operation)
    http["response"] = httpx.Response(200, json=data)
    kwargs = {"source": source, "operation": operation}
    expected_params = {}
    suffix = operation.replace("_", "-")
    if operation != "search":
        kwargs.update(from_date="2026-10-01", to_date="2026-10-07")
        expected_params.update({"from": "2026-10-01", "to": "2026-10-07"})
    if operation in ("trending", "search"):
        kwargs["limit"] = 5
        expected_params["limit"] = "5"
    if operation == "asset":
        kwargs["asset"] = "BTC" if source == "reddit_crypto" else "AAPL"
        suffix = "token/BTC" if source == "reddit_crypto" else "stock/AAPL"
    elif operation == "compare":
        kwargs["assets"] = ["BTC", "ETH"] if source == "reddit_crypto" else ["AAPL", "MSFT"]
        expected_params["symbols" if source == "reddit_crypto" else "tickers"] = ",".join(kwargs["assets"])
    elif operation == "search":
        kwargs["query"] = "apple"
        expected_params["q"] = "apple"

    result = tool_class(api_key=KEY).safe_run(**kwargs)
    assert isinstance(result, ToolResult)
    assert result.success is True
    assert result.error is None
    assert result.output == {
        "source": source, "operation": operation,
        "requested_period": {"from": kwargs.get("from_date"), "to": kwargs.get("to_date")},
        "data": data,
    }
    assert len(http["requests"]) == 1
    request = http["requests"][0]
    assert request.method == "GET"
    assert str(request.url).split("?")[0] == "https://api.adanos.com" + SOURCES[source] + "/" + suffix
    assert dict(request.url.params) == expected_params
    assert request.headers["X-API-Key"] == KEY
    assert request.extensions["timeout"] == dict.fromkeys(["connect", "read", "write", "pool"], 30.0)
    assert http["clients"][0].follow_redirects is False
    assert KEY not in str(result.to_dict())


def test_native_catalogue_schema_and_callable(tool_class, http):
    assert "AdanosTool" in get_tool_names()
    entry = next(e for e in list_tools() if e.name == "AdanosTool")
    assert entry.module == "adanos_tool"
    assert entry.extras == ("adanos",)
    tool = tool_class(api_key=KEY)
    assert isinstance(tool, BaseTool)
    assert tool.validate() and tool.validate_schema_roundtrip()
    schema = tool.get_schema()["function"]
    assert schema["name"] == "adanos_query"
    params = schema["parameters"]
    assert set(params["properties"]) == {
        "source", "operation", "asset", "assets", "query", "from_date", "to_date", "limit",
    }
    assert set(params["required"]) == {"source", "operation"}
    assert params["properties"]["source"]["enum"] == list(SOURCES)
    assert params["properties"]["operation"]["enum"] == OPERATIONS
    assert params["properties"]["assets"]["anyOf"][0] == {"type": "array", "items": {"type": "string"}}
    assert KEY not in json.dumps(schema) + repr(tool) + str(tool)
    assert tool(source="reddit_stocks", operation="trending").output["data"] == []


def test_unconfigured_has_no_network(tool_class, http):
    result = tool_class().safe_run(source="reddit_stocks", operation="trending")
    assert result.success is False and result.output is None
    assert "ADANOS_API_KEY" in result.error
    assert not http["clients"] and not http["requests"]


@pytest.mark.parametrize("key", ["test-secret-\N{SNOWMAN}", "test-secret-\n", "test-secret-\r", 123])
def test_invalid_key_never_leaks_or_requests(tool_class, http, key, caplog):
    result = tool_class(api_key=key).safe_run(source="reddit_stocks", operation="trending")
    assert not result.success and result.output is None
    assert "test-secret" not in str(result.to_dict()) + caplog.text
    assert not http["clients"] and not http["requests"]


def test_env_key_and_per_call_cleanup(tool_class, http, monkeypatch):
    monkeypatch.setenv("ADANOS_API_KEY", KEY)
    tool = tool_class()
    for _ in range(2):
        assert tool(source="reddit_stocks", operation="trending").success
    assert len(http["clients"]) == 2
    assert http["clients"][0] is not http["clients"][1]
    assert http["closed"] == 2


@pytest.mark.parametrize("status", [200, 429])
def test_agent_execute_tool_without_model_call(tool_class, http, monkeypatch, status):
    monkeypatch.setenv("PRAISONAI_TELEMETRY_DISABLED", "true")
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    from praisonaiagents import Agent

    http["response"] = httpx.Response(status, json=[] if status == 200 else {"detail": KEY})
    agent = Agent(name="Researcher", tools=[tool_class(api_key=KEY)])
    result = agent.execute_tool("adanos_query", {"source": "reddit_stocks", "operation": "trending"})
    assert isinstance(result, ToolResult)
    assert result.success is (status == 200)
    assert KEY not in str(result.to_dict())
    assert len(http["requests"]) == 1


@pytest.mark.parametrize("status", [200, 429])
def test_agent_chat_dispatches_adanos_without_model_call(tool_class, http, monkeypatch, status):
    from openai.resources.chat.completions import AsyncCompletions, Completions
    from openai.types.chat import ChatCompletion
    from praisonaiagents import Agent

    monkeypatch.setenv("PRAISONAI_TELEMETRY_DISABLED", "true")
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    completions = []

    def no_network(*args, **kwargs):
        pytest.fail("Unexpected network or synchronous model call")

    async def complete(self, **kwargs):
        completions.append(deepcopy(kwargs))
        message = {"role": "assistant", "content": "Offline research complete."}
        finish_reason = "stop"
        if len(completions) == 1 and kwargs.get("tools"):
            message.update(content=None, tool_calls=[{
                "id": "call_adanos", "type": "function",
                "function": {
                    "name": "adanos_query",
                    "arguments": json.dumps({"source": "reddit_stocks", "operation": "trending"}),
                },
            }])
            finish_reason = "tool_calls"
        return ChatCompletion(
            id="offline-completion", created=0, model="gpt-3.5-turbo", object="chat.completion",
            choices=[{"index": 0, "finish_reason": finish_reason, "message": message}],
        )

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket.socket, "connect_ex", no_network)
    monkeypatch.setattr(Completions, "create", no_network)
    monkeypatch.setattr(AsyncCompletions, "create", complete)
    http["response"] = httpx.Response(status, json=[] if status == 200 else {"detail": KEY})
    agent = Agent(name="Researcher", tools=[tool_class(api_key=KEY)],
                  model="gpt-3.5-turbo", api_key="offline-model-placeholder",
                  reflection=False, output="silent")

    assert agent.chat("Find trending Reddit stocks.", stream=False) == "Offline research complete."
    advertised = completions[0].get("tools", [])
    assert len(advertised) == 1
    assert advertised[0]["type"] == "function"
    function = advertised[0]["function"]
    assert function["name"] == "adanos_query"
    parameters = function["parameters"]
    assert set(parameters["required"]) == {"source", "operation"}
    assert set(parameters["properties"]) == {
        "source", "operation", "asset", "assets", "query", "from_date", "to_date", "limit",
    }
    assert parameters["properties"]["source"]["enum"] == list(SOURCES)
    assert parameters["properties"]["operation"]["enum"] == OPERATIONS
    assert len(completions) == 2
    replies = [m for m in completions[1]["messages"] if m["role"] == "tool"]
    expected = ("{'source': 'reddit_stocks', 'operation': 'trending', "
                "'requested_period': {'from': None, 'to': None}, 'data': []}"
                if status == 200 else "Error: Adanos HTTP 429.")
    assert replies == [{"role": "tool", "tool_call_id": "call_adanos",
                        "content": json.dumps({"result": expected})}]
    assert KEY not in str(completions)
    assert len(http["requests"]) == 1
    assert http["requests"][0].url.path == "/reddit/stocks/v1/trending"
    assert http["requests"][0].headers["X-API-Key"] == KEY


@pytest.mark.parametrize("asset", ["brk", "abx.DE", "BRK.A", "$AAPL", "BRK-B"])
def test_news_keys_are_not_normalized(tool_class, http, asset):
    http["response"] = httpx.Response(422, json={"detail": "provider syntax rejection"})
    result = tool_class(api_key=KEY)(source="news_stocks", operation="asset", asset=asset)
    assert not result.success
    assert http["requests"][0].url.path == "/news/stocks/v1/stock/" + asset
    assert "422" in result.error


@pytest.mark.parametrize("override", [
    {"source": "other"}, {"source": []}, {"operation": "mentions"}, {"operation": None},
    {"from_date": "20261001"}, {"from_date": "2026-02-30"}, {"to_date": ""},
    {"from_date": "2026-10-08", "to_date": "2026-10-01"},
    {"from_date": 1}, {"limit": 0}, {"limit": 101}, {"limit": True}, {"limit": "5"},
    {"operation": "asset"}, {"operation": "asset", "asset": "../search"},
    {"operation": "asset", "asset": ".."}, {"operation": "asset", "asset": "%2e%2e"},
    {"operation": "asset", "asset": "AAPL?x=1"},
    {"operation": "asset", "asset": "https://example.com"},
    {"operation": "asset", "asset": "AAPL\n"}, {"operation": "asset", "asset": 123},
    {"operation": "asset", "asset": "AAPL", "limit": 5},
    {"operation": "compare"}, {"operation": "compare", "assets": []},
    {"operation": "compare", "assets": "AAPL,MSFT"},
    {"operation": "compare", "assets": ["AAPL"] * 11},
    {"operation": "compare", "assets": ["AAPL,MSFT"]},
    {"operation": "compare", "assets": ["AAPL", 1]},
    {"operation": "search"}, {"operation": "search", "query": "$ A "},
    {"operation": "search", "query": 3},
    {"operation": "search", "query": "apple", "limit": 51},
    {"operation": "search", "query": "apple", "from_date": "2026-10-01"},
    {"source": "news_stocks", "operation": "search", "query": "a" * 101},
    {"source": "polymarket_stocks", "operation": "search", "query": "a" * 51},
    {"operation": "market_sentiment", "limit": 10},
    {"asset": "AAPL"}, {"assets": ["AAPL"]}, {"query": "apple"},
])
def test_invalid_inputs_do_not_request(tool_class, http, override):
    args = {"source": "reddit_stocks", "operation": "trending", **override}
    result = tool_class(api_key=KEY).safe_run(**args)
    assert not result.success and result.output is None and result.error
    assert not http["requests"] and not http["clients"]


@pytest.mark.parametrize("status", [301, 302, 307, 308, 401, 403, 404, 422, 429, 500, 502, 503, 504])
def test_http_errors_are_not_evidence(tool_class, http, status, caplog):
    http["response"] = httpx.Response(status, text="private provider body " + KEY,
                                      headers={"Location": "https://other.example/" + KEY})
    result = tool_class(api_key=KEY).safe_run(source="reddit_stocks", operation="trending")
    assert not result.success and result.output is None
    assert str(status) in result.error
    assert "Error:" in str(result)
    assert KEY not in str(result.to_dict()) + caplog.text
    assert "private provider body" not in str(result)
    assert len(http["requests"]) == 1
    assert http["closed"] == 1


@pytest.mark.parametrize("error", [httpx.ReadTimeout(KEY), httpx.ConnectError(KEY)])
def test_transport_errors_are_safe_and_close(tool_class, http, error, caplog):
    http["response"] = error
    result = tool_class(api_key=KEY).safe_run(source="reddit_stocks", operation="trending")
    assert not result.success and result.output is None and result.error
    assert KEY not in str(result.to_dict()) + caplog.text
    assert len(http["requests"]) == 1 and http["closed"] == 1


@pytest.mark.parametrize("operation,data", [
    ("trending", {}), ("trending", [1]), ("trending", [{"detail": "error"}]),
    ("asset", []), ("asset", {"detail": "error"}),
    ("compare", {"period_days": 7, "stocks": {}}),
    ("search", {"query": "apple", "count": 0, "period_days": 7, "results": {}}),
    ("market_sentiment", []), ("market_sentiment", {"detail": "error"}),
])
def test_wrong_success_shapes_fail(tool_class, http, operation, data):
    http["response"] = httpx.Response(200, json=data)
    result = tool_class(api_key=KEY).safe_run(
        source="reddit_stocks", operation=operation,
        **({"asset": "AAPL"} if operation == "asset" else
           {"assets": ["AAPL", "MSFT"]} if operation == "compare" else
           {"query": "apple"} if operation == "search" else {}),
    )
    assert not result.success and result.output is None
    assert http["closed"] == 1


@pytest.mark.parametrize("body", [b"not JSON", b"null", b'"string"', b"0"])
def test_malformed_success_fails(tool_class, http, body):
    http["response"] = httpx.Response(200, content=body)
    result = tool_class(api_key=KEY).safe_run(source="reddit_stocks", operation="trending")
    assert not result.success and result.output is None
    assert http["closed"] == 1


@pytest.mark.parametrize("source", SOURCES)
def test_market_sentiment_requires_activity_not_just_score(tool_class, http, source):
    http["response"] = httpx.Response(200, json={"buzz_score": None})
    result = tool_class(api_key=KEY).safe_run(source=source, operation="market_sentiment")
    assert not result.success and result.output is None
