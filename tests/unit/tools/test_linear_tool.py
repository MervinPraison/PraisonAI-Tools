"""Unit tests for LinearTool."""

import os
from unittest.mock import MagicMock, patch

from praisonai_tools.tools.linear_tool import LinearTool, list_linear_issues


# ── Auth header ─────────────────────────────────────────────────────


class TestAuthHeader:
    def test_personal_api_key_sent_raw(self):
        tool = LinearTool(api_key="lin_api_xyz")
        assert tool._auth_header() == "lin_api_xyz"

    def test_oauth_token_gets_bearer_prefix(self):
        tool = LinearTool(oauth_token="oauth_abc")
        assert tool._auth_header() == "Bearer oauth_abc"

    def test_api_key_takes_precedence_over_oauth(self):
        tool = LinearTool(api_key="lin_api_xyz", oauth_token="oauth_abc")
        assert tool._auth_header() == "lin_api_xyz"

    def test_no_credentials_returns_none(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = LinearTool()
            assert tool._auth_header() is None

    def test_env_var_fallback_personal(self):
        with patch.dict(os.environ, {"LINEAR_API_KEY": "envkey"}, clear=True):
            tool = LinearTool()
            assert tool._auth_header() == "envkey"

    def test_env_var_fallback_oauth(self):
        with patch.dict(os.environ, {"LINEAR_OAUTH_TOKEN": "envoauth"}, clear=True):
            tool = LinearTool()
            assert tool._auth_header() == "Bearer envoauth"


# ── _graphql wiring ─────────────────────────────────────────────────


def _mock_response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    return resp


class TestGraphQL:
    def test_missing_credentials_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = LinearTool()
            result = tool._graphql("query { viewer { id } }")
            assert result == {
                "error": "LINEAR_API_KEY or LINEAR_OAUTH_TOKEN required"
            }

    def test_sends_personal_api_key_header(self):
        tool = LinearTool(api_key="lin_api_xyz")
        with patch("requests.post") as post:
            post.return_value = _mock_response({"data": {"ok": True}})
            tool._graphql("query { x }", {"v": 1})
            kwargs = post.call_args.kwargs
            assert kwargs["headers"]["Authorization"] == "lin_api_xyz"
            assert kwargs["json"] == {"query": "query { x }", "variables": {"v": 1}}

    def test_sends_bearer_for_oauth(self):
        tool = LinearTool(oauth_token="oauth_abc")
        with patch("requests.post") as post:
            post.return_value = _mock_response({"data": {"ok": True}})
            tool._graphql("query { x }")
            assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer oauth_abc"

    def test_handles_request_exception(self):
        tool = LinearTool(api_key="x")
        with patch("requests.post", side_effect=RuntimeError("boom")):
            assert tool._graphql("q") == {"error": "boom"}


# ── list_issues ─────────────────────────────────────────────────────


class TestListIssues:
    def test_returns_normalised_issues(self):
        tool = LinearTool(api_key="x")
        payload = {
            "data": {
                "issues": {
                    "nodes": [
                        {
                            "id": "i1",
                            "title": "Bug",
                            "state": {"name": "Todo"},
                            "priority": 2,
                            "assignee": {"name": "Alice"},
                        },
                        {
                            "id": "i2",
                            "title": "Feat",
                            "state": {"name": "Done"},
                            "priority": 0,
                            "assignee": None,
                        },
                    ]
                }
            }
        }
        with patch("requests.post", return_value=_mock_response(payload)):
            issues = tool.list_issues(limit=2)

        assert len(issues) == 2
        assert issues[0]["assignee"] == "Alice"
        assert issues[1]["assignee"] is None
        assert issues[1]["state"] == "Done"

    def test_propagates_error(self):
        tool = LinearTool(api_key="x")
        with patch("requests.post", side_effect=RuntimeError("net")):
            issues = tool.list_issues()
        assert issues == [{"error": "net"}]


# ── get_issue ───────────────────────────────────────────────────────


class TestGetIssue:
    def test_requires_issue_id(self):
        tool = LinearTool(api_key="x")
        assert tool.get_issue(issue_id="") == {"error": "issue_id required"}

    def test_returns_normalised_issue(self):
        tool = LinearTool(api_key="x")
        payload = {
            "data": {
                "issue": {
                    "id": "i1",
                    "title": "T",
                    "description": "D",
                    "state": {"name": "Todo"},
                    "priority": 1,
                    "assignee": {"name": "A"},
                }
            }
        }
        with patch("requests.post", return_value=_mock_response(payload)):
            issue = tool.get_issue(issue_id="i1")
        assert issue["title"] == "T"
        assert issue["state"] == "Todo"
        assert issue["assignee"] == "A"


# ── create_issue ────────────────────────────────────────────────────


class TestCreateIssue:
    def test_requires_title(self):
        tool = LinearTool(api_key="x")
        assert tool.create_issue(title="", team_id="t") == {"error": "title required"}

    def test_requires_team_id(self):
        tool = LinearTool(api_key="x")
        assert tool.create_issue(title="T") == {"error": "team_id required"}

    def test_success(self):
        tool = LinearTool(api_key="x")
        payload = {
            "data": {"issueCreate": {"success": True, "issue": {"id": "i1", "title": "T"}}}
        }
        with patch("requests.post", return_value=_mock_response(payload)) as post:
            result = tool.create_issue(title="T", team_id="team1", description="D")

        sent = post.call_args.kwargs["json"]["variables"]["input"]
        assert sent == {"title": "T", "teamId": "team1", "description": "D"}
        assert result == {"success": True, "id": "i1"}

    def test_failure(self):
        tool = LinearTool(api_key="x")
        with patch(
            "requests.post",
            return_value=_mock_response({"data": {"issueCreate": {"success": False}}}),
        ):
            assert tool.create_issue(title="T", team_id="t") == {
                "error": "Failed to create issue"
            }


# ── update_issue ────────────────────────────────────────────────────


class TestUpdateIssue:
    def test_requires_issue_id(self):
        tool = LinearTool(api_key="x")
        assert tool.update_issue(issue_id="") == {"error": "issue_id required"}

    def test_requires_at_least_one_field(self):
        tool = LinearTool(api_key="x")
        assert tool.update_issue(issue_id="i1") == {"error": "no fields to update"}

    def test_only_provided_fields_in_input(self):
        tool = LinearTool(api_key="x")
        payload = {
            "data": {"issueUpdate": {"success": True, "issue": {"id": "i1", "title": "New"}}}
        }
        with patch("requests.post", return_value=_mock_response(payload)) as post:
            result = tool.update_issue(issue_id="i1", title="New", state_id="s1")

        sent = post.call_args.kwargs["json"]["variables"]["input"]
        assert sent == {"title": "New", "stateId": "s1"}
        assert result == {"success": True, "id": "i1", "title": "New"}

    def test_failure(self):
        tool = LinearTool(api_key="x")
        with patch(
            "requests.post",
            return_value=_mock_response({"data": {"issueUpdate": {"success": False}}}),
        ):
            assert tool.update_issue(issue_id="i1", title="T") == {
                "error": "Failed to update issue"
            }


# ── add_comment ─────────────────────────────────────────────────────


class TestAddComment:
    def test_requires_issue_id(self):
        tool = LinearTool(api_key="x")
        assert tool.add_comment(issue_id="", body="hi") == {"error": "issue_id required"}

    def test_requires_body(self):
        tool = LinearTool(api_key="x")
        assert tool.add_comment(issue_id="i1", body="") == {"error": "body required"}

    def test_success(self):
        tool = LinearTool(api_key="x")
        payload = {
            "data": {
                "commentCreate": {
                    "success": True,
                    "comment": {"id": "c1", "url": "https://linear.app/c/c1"},
                }
            }
        }
        with patch("requests.post", return_value=_mock_response(payload)) as post:
            result = tool.add_comment(issue_id="i1", body="hello")

        sent = post.call_args.kwargs["json"]["variables"]["input"]
        assert sent == {"issueId": "i1", "body": "hello"}
        assert result == {"success": True, "id": "c1", "url": "https://linear.app/c/c1"}


# ── list_teams / list_cycles / list_issue_states ────────────────────


class TestListTeams:
    def test_returns_teams(self):
        tool = LinearTool(api_key="x")
        payload = {
            "data": {
                "teams": {
                    "nodes": [
                        {"id": "t1", "name": "Eng", "key": "ENG"},
                        {"id": "t2", "name": "Design", "key": "DES"},
                    ]
                }
            }
        }
        with patch("requests.post", return_value=_mock_response(payload)):
            teams = tool.list_teams()
        assert len(teams) == 2
        assert teams[0]["key"] == "ENG"


class TestListCycles:
    def test_requires_team_id(self):
        tool = LinearTool(api_key="x")
        assert tool.list_cycles(team_id="") == [{"error": "team_id required"}]

    def test_returns_cycles(self):
        tool = LinearTool(api_key="x")
        payload = {
            "data": {
                "team": {
                    "cycles": {
                        "nodes": [
                            {
                                "id": "c1",
                                "name": "C1",
                                "number": 1,
                                "startsAt": "2026-01-01",
                                "endsAt": "2026-01-15",
                            }
                        ]
                    }
                }
            }
        }
        with patch("requests.post", return_value=_mock_response(payload)):
            cycles = tool.list_cycles(team_id="t1")
        assert len(cycles) == 1
        assert cycles[0]["number"] == 1


class TestListIssueStates:
    def test_requires_team_id(self):
        tool = LinearTool(api_key="x")
        assert tool.list_issue_states(team_id="") == [{"error": "team_id required"}]

    def test_returns_states(self):
        tool = LinearTool(api_key="x")
        payload = {
            "data": {
                "team": {
                    "states": {
                        "nodes": [
                            {"id": "s1", "name": "Todo", "type": "unstarted"},
                            {"id": "s2", "name": "Done", "type": "completed"},
                        ]
                    }
                }
            }
        }
        with patch("requests.post", return_value=_mock_response(payload)):
            states = tool.list_issue_states(team_id="t1")
        assert [s["name"] for s in states] == ["Todo", "Done"]


# ── run() dispatcher ────────────────────────────────────────────────


class TestRunDispatcher:
    def test_unknown_action(self):
        tool = LinearTool(api_key="x")
        assert tool.run(action="bogus") == {"error": "Unknown action: bogus"}

    def test_routes_update_issue(self):
        tool = LinearTool(api_key="x")
        with patch.object(tool, "update_issue", return_value={"ok": True}) as m:
            out = tool.run(action="update_issue", issue_id="i1", title="T")
        m.assert_called_once_with(issue_id="i1", title="T")
        assert out == {"ok": True}

    def test_routes_add_comment(self):
        tool = LinearTool(api_key="x")
        with patch.object(tool, "add_comment", return_value={"ok": True}) as m:
            tool.run(action="add_comment", issue_id="i1", body="hi")
        m.assert_called_once_with(issue_id="i1", body="hi")

    def test_routes_list_cycles(self):
        tool = LinearTool(api_key="x")
        with patch.object(tool, "list_cycles", return_value=[]) as m:
            tool.run(action="list_cycles", team_id="t1", limit=5)
        m.assert_called_once_with(team_id="t1", limit=5)

    def test_routes_list_issue_states(self):
        tool = LinearTool(api_key="x")
        with patch.object(tool, "list_issue_states", return_value=[]) as m:
            tool.run(action="list-issue-states", team_id="t1")
        m.assert_called_once_with(team_id="t1")


# ── Module-level helper ─────────────────────────────────────────────


class TestListLinearIssuesHelper:
    def test_delegates_to_tool(self):
        with patch.object(LinearTool, "list_issues", return_value=["x"]) as m:
            assert list_linear_issues(limit=5) == ["x"]
        m.assert_called_once_with(limit=5)
