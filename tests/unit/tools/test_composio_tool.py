"""Unit tests for Composio tools."""

import os
from unittest.mock import MagicMock, patch

from praisonai_tools.tools.composio_tool import (
    ComposioTool,
    ComposioTools,
    _check_composio_available,
    composio_execute,
    composio_list_apps,
    composio_tools,
)


class TestCheckComposioAvailable:
    def test_missing_package(self):
        with patch("praisonai_tools.tools.composio_tool.util.find_spec", return_value=None):
            ok, msg = _check_composio_available()
        assert ok is False
        assert "not installed" in msg

    def test_missing_api_key(self):
        with patch("praisonai_tools.tools.composio_tool.util.find_spec", return_value=MagicMock()):
            with patch.dict(os.environ, {}, clear=True):
                ok, msg = _check_composio_available()
        assert ok is False
        assert "COMPOSIO_API_KEY" in msg

    def test_available(self):
        with patch("praisonai_tools.tools.composio_tool.util.find_spec", return_value=MagicMock()):
            with patch.dict(os.environ, {"COMPOSIO_API_KEY": "test-key"}, clear=True):
                ok, msg = _check_composio_available()
        assert ok is True
        assert msg is None


class TestComposioTools:
    def test_get_tools_unavailable_returns_empty(self):
        with patch(
            "praisonai_tools.tools.composio_tool._check_composio_available",
            return_value=(False, "missing"),
        ):
            assert ComposioTools().get_tools(apps=["github"]) == []

    def test_get_tools_new_sdk(self):
        mock_tool = MagicMock()
        mock_client = MagicMock()
        mock_client.tools.get.return_value = [mock_tool]

        with patch(
            "praisonai_tools.tools.composio_tool._check_composio_available",
            return_value=(True, None),
        ):
            tools = ComposioTools(api_key="k")
            with patch.object(tools, "_get_client", return_value=mock_client):
                result = tools.get_tools(apps=["github"])

        assert result == [mock_tool]
        mock_client.tools.get.assert_called_once_with(apps=["github"])

    def test_list_apps(self):
        app = MagicMock(key="github")
        mock_client = MagicMock()
        mock_client.apps.get.return_value = [app]

        with patch(
            "praisonai_tools.tools.composio_tool._check_composio_available",
            return_value=(True, None),
        ):
            tools = ComposioTools(api_key="k")
            with patch.object(tools, "_get_client", return_value=mock_client):
                assert tools.list_apps() == ["github"]


class TestStandaloneFunctions:
    def test_composio_tools_delegates(self):
        with patch.object(ComposioTools, "get_tools", return_value=["t1"]) as mock_get:
            assert composio_tools(apps=["slack"]) == ["t1"]
        mock_get.assert_called_once_with(apps=["slack"], actions=None, tags=None, user_id=None)

    def test_composio_list_apps_delegates(self):
        with patch.object(ComposioTools, "list_apps", return_value=["github"]) as mock_list:
            assert composio_list_apps() == ["github"]
        mock_list.assert_called_once_with()


class TestComposioTool:
    def test_execute_requires_action_name(self):
        assert ComposioTool().execute(action_name="", params={}) == {"error": "action_name is required"}

    def test_composio_execute_delegates(self):
        with patch.object(ComposioTool, "execute", return_value={"result": "ok"}) as mock_exec:
            assert composio_execute("GITHUB_STAR", {"repo": "x"}) == {"result": "ok"}
        mock_exec.assert_called_once_with(action_name="GITHUB_STAR", params={"repo": "x"})
