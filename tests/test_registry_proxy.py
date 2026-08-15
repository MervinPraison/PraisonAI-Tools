"""Unit tests for the tool-registry proxy connector."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture(autouse=True)
def reset_session_spend():
    """Isolate cumulative-spend state between tests."""
    from praisonai_tools.registry_proxy import registry_proxy as mod

    mod._SESSION_SPEND.clear()
    yield
    mod._SESSION_SPEND.clear()


@pytest.fixture
def mock_httpx():
    """Mock httpx module with proper exception classes."""
    mock_module = MagicMock()
    mock_module.TimeoutException = type("TimeoutException", (Exception,), {})

    class MockHTTPStatusError(Exception):
        def __init__(self, message, request=None, response=None):
            super().__init__(message)
            self.request = request
            self.response = response

    mock_module.HTTPStatusError = MockHTTPStatusError
    with patch.dict("sys.modules", {"httpx": mock_module}):
        yield mock_module


class TestConfiguration:
    def test_disabled_when_unconfigured(self):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        with patch.dict(os.environ, {}, clear=True):
            tool = RegistryProxyTool()
            result = tool.search("backlinks for a domain")
            assert "not configured" in result["error"]

    def test_reads_env_vars(self):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        with patch.dict(os.environ, {
            "TOOL_PROXY_URL": "https://registry.example.com/",
            "TOOL_PROXY_TOKEN": "secret-token",
        }):
            tool = RegistryProxyTool()
            assert tool.proxy_url == "https://registry.example.com"
            assert tool.token == "secret-token"
            assert tool._headers()["Authorization"] == "Bearer secret-token"

    def test_explicit_args_override_env(self):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        tool = RegistryProxyTool(proxy_url="https://self.host/", token="tok")
        assert tool.proxy_url == "https://self.host"
        assert tool.token == "tok"

    def test_env_token_not_leaked_to_supplied_url(self):
        """Security: an agent-supplied proxy_url must not receive the env token."""
        from praisonai_tools.registry_proxy import RegistryProxyTool

        with patch.dict(os.environ, {
            "TOOL_PROXY_URL": "https://trusted.example.com",
            "TOOL_PROXY_TOKEN": "secret-token",
        }):
            tool = RegistryProxyTool(proxy_url="https://attacker.example.com")
            assert tool.proxy_url == "https://attacker.example.com"
            assert tool.token is None
            assert "Authorization" not in tool._headers()

    def test_env_token_used_for_env_url(self):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        with patch.dict(os.environ, {
            "TOOL_PROXY_URL": "https://trusted.example.com",
            "TOOL_PROXY_TOKEN": "secret-token",
        }):
            tool = RegistryProxyTool()
            assert tool._headers()["Authorization"] == "Bearer secret-token"


class TestAuthHeader:
    def test_auth_header_configurable(self):
        """Default sends Bearer; a custom header name sends the raw token."""
        from praisonai_tools.registry_proxy import RegistryProxyTool

        default = RegistryProxyTool(proxy_url="https://r.example.com", token="tok")
        assert default._headers()["Authorization"] == "Bearer tok"
        assert "X-Treg-Token" not in default._headers()

        custom = RegistryProxyTool(
            proxy_url="https://r.example.com", token="tok", auth_header="X-Treg-Token"
        )
        headers = custom._headers()
        assert headers["X-Treg-Token"] == "tok"
        assert "Authorization" not in headers

    def test_auth_header_from_env(self):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        with patch.dict(os.environ, {
            "TOOL_PROXY_URL": "https://trusted.example.com",
            "TOOL_PROXY_TOKEN": "secret-token",
            "TOOL_PROXY_AUTH_HEADER": "X-Treg-Token",
        }):
            tool = RegistryProxyTool()
            headers = tool._headers()
            assert headers["X-Treg-Token"] == "secret-token"
            assert "Authorization" not in headers


class TestSearch:
    def test_search_success(self, mock_httpx):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        response = Mock()
        response.json.return_value = {"matches": [{"id": "seo.backlinks"}]}
        response.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = response
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com", token="t")
        result = tool.search("backlinks for a domain")

        assert result["matches"][0]["id"] == "seo.backlinks"
        client.get.assert_called_once_with(
            "https://r.example.com/catalog/search",
            params={"q": "backlinks for a domain"},
            headers={"Content-Type": "application/json", "Authorization": "Bearer t"},
        )

    def test_search_requires_query(self):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        tool = RegistryProxyTool(proxy_url="https://r.example.com")
        assert tool.search("")["error"] == "query is required"


class TestDescribe:
    def test_describe_success(self, mock_httpx):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        response = Mock()
        response.json.return_value = {"id": "seo.backlinks", "price_per_call": 0.01}
        response.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = response
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com")
        result = tool.describe("seo.backlinks")

        assert result["price_per_call"] == 0.01
        client.get.assert_called_once_with(
            "https://r.example.com/catalog/endpoints/seo.backlinks",
            headers={"Content-Type": "application/json"},
        )

    def test_describe_uses_endpoints_path(self, mock_httpx):
        """The real registry route is /catalog/endpoints/{id}, not /catalog/{id}."""
        from praisonai_tools.registry_proxy import RegistryProxyTool

        response = Mock()
        response.json.return_value = {"id": "diffbot.people.enrich", "method": "GET"}
        response.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = response
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com", token="t")
        tool.describe("diffbot.people.enrich")

        client.get.assert_called_once_with(
            "https://r.example.com/catalog/endpoints/diffbot.people.enrich",
            headers={"Content-Type": "application/json", "Authorization": "Bearer t"},
        )

    def test_describe_path_configurable(self, mock_httpx):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        response = Mock()
        response.json.return_value = {"id": "seo.backlinks"}
        response.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = response
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(
            proxy_url="https://r.example.com",
            describe_path="/catalog/{tool_id}",
        )
        tool.describe("seo.backlinks")

        client.get.assert_called_once_with(
            "https://r.example.com/catalog/seo.backlinks",
            headers={"Content-Type": "application/json"},
        )

    def test_describe_path_from_env(self, mock_httpx):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        response = Mock()
        response.json.return_value = {"id": "seo.backlinks"}
        response.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = response
        mock_httpx.Client.return_value.__enter__.return_value = client

        with patch.dict(os.environ, {
            "TOOL_PROXY_URL": "https://r.example.com",
            "TOOL_PROXY_DESCRIBE_PATH": "/v2/endpoints/{tool_id}",
        }):
            tool = RegistryProxyTool()
            tool.describe("seo.backlinks")

        client.get.assert_called_once_with(
            "https://r.example.com/v2/endpoints/seo.backlinks",
            headers={"Content-Type": "application/json"},
        )

    def test_describe_path_missing_placeholder_errors(self, mock_httpx):
        """A template lacking {tool_id} must return an error, not silently misroute."""
        from praisonai_tools.registry_proxy import RegistryProxyTool

        client = Mock()
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(
            proxy_url="https://r.example.com",
            describe_path="/catalog/static",
        )
        result = tool.describe("seo.backlinks")

        assert "must contain '{tool_id}'" in result["error"]
        client.get.assert_not_called()

    def test_describe_path_malformed_template_errors(self, mock_httpx):
        """A malformed template must return an error instead of raising."""
        from praisonai_tools.registry_proxy import RegistryProxyTool

        client = Mock()
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(
            proxy_url="https://r.example.com",
            describe_path="/catalog/{tool_id}/{unknown}",
        )
        result = tool.describe("seo.backlinks")

        assert "Invalid describe path template" in result["error"]
        client.get.assert_not_called()

    def test_describe_encodes_tool_id(self, mock_httpx):
        """A tool_id with path-changing characters is URL-encoded."""
        from praisonai_tools.registry_proxy import RegistryProxyTool

        response = Mock()
        response.json.return_value = {"id": "x"}
        response.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = response
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com")
        tool.describe("../admin?x=1")

        client.get.assert_called_once_with(
            "https://r.example.com/catalog/endpoints/..%2Fadmin%3Fx%3D1",
            headers={"Content-Type": "application/json"},
        )


class TestCall:
    def test_call_success(self, mock_httpx):
        """Explicit method=POST skips describe and posts a JSON body."""
        from praisonai_tools.registry_proxy import RegistryProxyTool

        response = Mock()
        response.json.return_value = {"data": {"backlinks": 42}}
        response.raise_for_status.return_value = None
        client = Mock()
        client.request.return_value = response
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com", token="t")
        result = tool.call("seo.backlinks", {"domain": "example.com"}, method="POST")

        assert result["data"]["backlinks"] == 42
        client.request.assert_called_once_with(
            "POST",
            "https://r.example.com/call/seo.backlinks",
            json={"domain": "example.com"},
            headers={"Content-Type": "application/json", "Authorization": "Bearer t"},
        )
        client.get.assert_not_called()

    def test_call_requires_tool_id(self):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        tool = RegistryProxyTool(proxy_url="https://r.example.com")
        assert tool.call("")["error"] == "tool_id is required"

    def test_call_normalizes_explicit_method_whitespace(self, mock_httpx):
        """An explicit method with whitespace/casing is normalized (GET -> query)."""
        from praisonai_tools.registry_proxy import RegistryProxyTool

        response = Mock()
        response.json.return_value = {"data": {"ok": True}}
        response.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = response
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com")
        result = tool.call("t.id", {"q": "x"}, method=" get ")

        assert result["data"]["ok"] is True
        client.get.assert_called_once_with(
            "https://r.example.com/call/t.id",
            params={"q": "x"},
            headers={"Content-Type": "application/json"},
        )
        client.request.assert_not_called()

    def test_call_rejects_unsupported_method(self, mock_httpx):
        """An unsupported/mislabelled method is rejected before any request."""
        from praisonai_tools.registry_proxy import RegistryProxyTool

        client = Mock()
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com")
        result = tool.call("t.id", {}, method="TRACE")

        assert "Unsupported HTTP method 'TRACE'" in result["error"]
        client.get.assert_not_called()
        client.request.assert_not_called()

    def test_call_encodes_tool_id_in_url(self, mock_httpx):
        """A tool_id with path-changing characters is URL-encoded on /call."""
        from praisonai_tools.registry_proxy import RegistryProxyTool

        response = Mock()
        response.json.return_value = {"data": "ok"}
        response.raise_for_status.return_value = None
        client = Mock()
        client.request.return_value = response
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com")
        tool.call("../admin", {}, method="POST")

        client.request.assert_called_once_with(
            "POST",
            "https://r.example.com/call/..%2Fadmin",
            json={},
            headers={"Content-Type": "application/json"},
        )

    def test_call_derives_post_method_from_describe(self, mock_httpx):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        describe_resp = Mock()
        describe_resp.json.return_value = {"id": "seo.backlinks", "method": "POST"}
        describe_resp.raise_for_status.return_value = None
        call_resp = Mock()
        call_resp.json.return_value = {"data": {"backlinks": 42}}
        call_resp.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = describe_resp
        client.request.return_value = call_resp
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com", token="t")
        result = tool.call("seo.backlinks", {"domain": "example.com"})

        assert result["data"]["backlinks"] == 42
        client.request.assert_called_once_with(
            "POST",
            "https://r.example.com/call/seo.backlinks",
            json={"domain": "example.com"},
            headers={"Content-Type": "application/json", "Authorization": "Bearer t"},
        )

    def test_call_uses_declared_method(self, mock_httpx):
        """describe says GET -> GET with query params (no JSON body)."""
        from praisonai_tools.registry_proxy import RegistryProxyTool

        describe_resp = Mock()
        describe_resp.json.return_value = {
            "id": "diffbot.people.enrich", "method": "GET"
        }
        describe_resp.raise_for_status.return_value = None
        call_resp = Mock()
        call_resp.json.return_value = {"data": {"name": "Jane"}}
        call_resp.raise_for_status.return_value = None
        client = Mock()
        client.get.side_effect = [describe_resp, call_resp]
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com", token="t")
        result = tool.call("diffbot.people.enrich", {"query": "type=email"})

        assert result["data"]["name"] == "Jane"
        client.request.assert_not_called()
        # First get = describe, second get = the GET call with query params.
        assert client.get.call_count == 2
        call_args = client.get.call_args_list[1]
        assert call_args.args[0] == "https://r.example.com/call/diffbot.people.enrich"
        assert call_args.kwargs["params"] == {"query": "type=email"}

    def test_call_explicit_get_skips_describe(self, mock_httpx):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        call_resp = Mock()
        call_resp.json.return_value = {"data": "ok"}
        call_resp.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = call_resp
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com", token="t")
        result = tool.call("diffbot.people.enrich", {"q": "x"}, method="GET")

        assert result["data"] == "ok"
        client.get.assert_called_once_with(
            "https://r.example.com/call/diffbot.people.enrich",
            params={"q": "x"},
            headers={"Content-Type": "application/json", "Authorization": "Bearer t"},
        )

    def test_call_defaults_to_post_when_method_absent(self, mock_httpx):
        """describe omits method -> default to POST with JSON body."""
        from praisonai_tools.registry_proxy import RegistryProxyTool

        describe_resp = Mock()
        describe_resp.json.return_value = {"id": "seo.backlinks"}
        describe_resp.raise_for_status.return_value = None
        call_resp = Mock()
        call_resp.json.return_value = {"data": "ok"}
        call_resp.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = describe_resp
        client.request.return_value = call_resp
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com")
        result = tool.call("seo.backlinks", {"domain": "x"})

        assert result["data"] == "ok"
        client.request.assert_called_once_with(
            "POST",
            "https://r.example.com/call/seo.backlinks",
            json={"domain": "x"},
            headers={"Content-Type": "application/json"},
        )

    def test_guarded_call_works_on_get_endpoint(self, mock_httpx):
        """Regression: spend guard + GET endpoint end-to-end (describe fetched once)."""
        from praisonai_tools.registry_proxy import RegistryProxyTool

        describe_resp = Mock()
        describe_resp.json.return_value = {
            "id": "diffbot.people.enrich", "method": "GET", "price_per_call": 0.05
        }
        describe_resp.raise_for_status.return_value = None
        call_resp = Mock()
        call_resp.json.return_value = {"data": "ok", "price_per_call": 0.05}
        call_resp.raise_for_status.return_value = None
        client = Mock()
        client.get.side_effect = [describe_resp, call_resp]
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(
            proxy_url="https://r.example.com", max_session_spend=1.0
        )
        result = tool.call("diffbot.people.enrich", {"query": "type=email"})

        assert result["data"] == "ok"
        assert tool._session_spend == pytest.approx(0.05)
        client.request.assert_not_called()
        # describe reused from the guard: exactly one describe + one GET call.
        assert client.get.call_count == 2
        assert client.get.call_args_list[1].kwargs["params"] == {"query": "type=email"}


class TestErrorTaxonomy:
    def test_auth_error(self, mock_httpx):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        resp = Mock()
        resp.status_code = 401
        resp.text = "Unauthorized"
        client = Mock()
        client.get.side_effect = mock_httpx.HTTPStatusError("401", response=resp)
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com", token="bad")
        result = tool.search("x")
        assert "Authentication failed" in result["error"]

    def test_insufficient_balance_error(self, mock_httpx):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        resp = Mock()
        resp.status_code = 402
        resp.text = "Payment Required"
        client = Mock()
        client.request.side_effect = mock_httpx.HTTPStatusError("402", response=resp)
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com")
        result = tool.call("seo.backlinks", {}, method="POST")
        assert "Insufficient balance" in result["error"]

    def test_upstream_4xx_passthrough(self, mock_httpx):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        resp = Mock()
        resp.status_code = 404
        resp.text = "Not Found"
        client = Mock()
        client.request.side_effect = mock_httpx.HTTPStatusError("404", response=resp)
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com")
        result = tool.call("seo.backlinks", {}, method="POST")
        assert "HTTP 404" in result["error"]

    def test_timeout_error(self, mock_httpx):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        client = Mock()
        client.get.side_effect = mock_httpx.TimeoutException("timed out")
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com", timeout=5.0)
        result = tool.search("x")
        assert "timed out after 5.0" in result["error"]

    def test_missing_httpx(self):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        tool = RegistryProxyTool(proxy_url="https://r.example.com")
        with patch.dict("sys.modules", {"httpx": None}):
            with patch("builtins.__import__", side_effect=ImportError("no httpx")):
                result = tool.search("x")
                assert "httpx not installed" in result["error"]
                assert "praisonai-tools[registry-proxy]" in result["error"]


class TestSpendGuards:
    def test_max_cost_per_call_denies(self, mock_httpx):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        describe_resp = Mock()
        describe_resp.json.return_value = {"id": "seo.backlinks", "price_per_call": 0.50}
        describe_resp.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = describe_resp
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com", max_cost_per_call=0.10)
        result = tool.call("seo.backlinks", {})
        assert "exceeds max_cost_per_call" in result["error"]
        client.request.assert_not_called()

    def test_max_session_spend_denies(self, mock_httpx):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        describe_resp = Mock()
        describe_resp.json.return_value = {"price_per_call": 0.60}
        describe_resp.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = describe_resp
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com", max_session_spend=1.0)
        tool._session_spend = 0.50
        result = tool.call("seo.backlinks", {})
        assert "max_session_spend" in result["error"]
        client.request.assert_not_called()

    def test_within_budget_allows_and_tracks_spend(self, mock_httpx):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        describe_resp = Mock()
        describe_resp.json.return_value = {"price_per_call": 0.05}
        describe_resp.raise_for_status.return_value = None
        call_resp = Mock()
        call_resp.json.return_value = {"data": "ok", "price_per_call": 0.05}
        call_resp.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = describe_resp
        client.request.return_value = call_resp
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com", max_session_spend=1.0)
        result = tool.call("seo.backlinks", {})
        assert result["data"] == "ok"
        assert tool._session_spend == pytest.approx(0.05)

    @pytest.mark.parametrize("field", ["price_per_call", "price", "cost"])
    def test_budget_check_accepts_price_and_cost_fields(self, mock_httpx, field):
        """Budget check tolerates price_per_call/price/cost, matching recording."""
        from praisonai_tools.registry_proxy import RegistryProxyTool

        describe_resp = Mock()
        describe_resp.json.return_value = {"id": "seo.backlinks", field: 0.05}
        describe_resp.raise_for_status.return_value = None
        call_resp = Mock()
        call_resp.json.return_value = {"data": "ok", field: 0.05}
        call_resp.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = describe_resp
        client.request.return_value = call_resp
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com", max_session_spend=1.0)
        result = tool.call("seo.backlinks", {})
        assert result["data"] == "ok"
        assert tool._session_spend == pytest.approx(0.05)

    def test_missing_price_fails_closed(self, mock_httpx):
        from praisonai_tools.registry_proxy import RegistryProxyTool

        describe_resp = Mock()
        describe_resp.json.return_value = {"id": "seo.backlinks"}
        describe_resp.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = describe_resp
        mock_httpx.Client.return_value.__enter__.return_value = client

        tool = RegistryProxyTool(proxy_url="https://r.example.com", max_cost_per_call=0.10)
        result = tool.call("seo.backlinks", {})
        assert "cannot enforce" in result["error"]
        client.request.assert_not_called()

    def test_session_spend_persists_across_registry_call(self, mock_httpx):
        """max_session_spend must accumulate across separate registry_call calls."""
        from praisonai_tools.registry_proxy import registry_call

        describe_resp = Mock()
        describe_resp.json.return_value = {"price_per_call": 0.60}
        describe_resp.raise_for_status.return_value = None
        call_resp = Mock()
        call_resp.json.return_value = {"data": "ok", "price_per_call": 0.60}
        call_resp.raise_for_status.return_value = None
        client = Mock()
        client.get.return_value = describe_resp
        client.request.return_value = call_resp
        mock_httpx.Client.return_value.__enter__.return_value = client

        first = registry_call(
            "seo.backlinks", {},
            proxy_url="https://r.example.com", token="t",
            max_session_spend=1.0,
        )
        assert first["data"] == "ok"

        second = registry_call(
            "seo.backlinks", {},
            proxy_url="https://r.example.com", token="t",
            max_session_spend=1.0,
        )
        assert "max_session_spend" in second["error"]


class TestDecoratedFunctions:
    @patch("praisonai_tools.registry_proxy.registry_proxy.RegistryProxyTool")
    def test_registry_search_function(self, mock_cls):
        from praisonai_tools.registry_proxy import registry_search

        instance = Mock()
        instance.search.return_value = {"matches": []}
        mock_cls.return_value = instance

        registry_search("q", proxy_url="https://r", token="t")
        mock_cls.assert_called_once_with(
            proxy_url="https://r", token="t", auth_header=None
        )
        instance.search.assert_called_once_with("q")

    @patch("praisonai_tools.registry_proxy.registry_proxy.RegistryProxyTool")
    def test_registry_call_function_passes_guards(self, mock_cls):
        from praisonai_tools.registry_proxy import registry_call

        instance = Mock()
        instance.call.return_value = {"data": "ok"}
        mock_cls.return_value = instance

        registry_call(
            "seo.backlinks",
            {"domain": "x"},
            proxy_url="https://r",
            token="t",
            max_cost_per_call=0.1,
            max_session_spend=1.0,
        )
        mock_cls.assert_called_once_with(
            proxy_url="https://r",
            token="t",
            max_cost_per_call=0.1,
            max_session_spend=1.0,
            auth_header=None,
            describe_path=None,
        )
        instance.call.assert_called_once_with("seo.backlinks", {"domain": "x"}, None)

    @patch("praisonai_tools.registry_proxy.registry_proxy.RegistryProxyTool")
    def test_registry_call_function_passes_method(self, mock_cls):
        from praisonai_tools.registry_proxy import registry_call

        instance = Mock()
        instance.call.return_value = {"data": "ok"}
        mock_cls.return_value = instance

        registry_call(
            "diffbot.people.enrich",
            {"query": "type=email"},
            proxy_url="https://r",
            token="t",
            method="GET",
        )
        instance.call.assert_called_once_with(
            "diffbot.people.enrich", {"query": "type=email"}, "GET"
        )


def test_smoke_import():
    from praisonai_tools.registry_proxy import (
        RegistryProxyTool,
        registry_search,
        registry_describe,
        registry_call,
    )

    assert callable(registry_search)
    assert callable(registry_describe)
    assert callable(registry_call)
    assert RegistryProxyTool().name == "registry_proxy"


@pytest.mark.integration
def test_live_smoke():
    """Gated live smoke test; skipped unless TOOL_PROXY_URL is configured."""
    proxy_url = os.getenv("TOOL_PROXY_URL")
    if not proxy_url:
        pytest.skip("TOOL_PROXY_URL not set")
    from praisonai_tools.registry_proxy import registry_search

    result = registry_search("backlinks for a domain")
    assert isinstance(result, dict)
    assert "error" not in result
