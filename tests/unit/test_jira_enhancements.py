"""Tests for Jira sprint operations (list, active, move issues)."""

import os
from unittest.mock import patch

ENV = {
    "JIRA_URL": "https://test.atlassian.net",
    "JIRA_EMAIL": "test@example.com",
    "JIRA_API_TOKEN": "super-secret-token",
}


class TestSprintOperations:
    @patch.dict(os.environ, ENV)
    def test_list_sprints(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request") as mock_req:
            mock_req.return_value = {
                "values": [
                    {"id": 42, "name": "Sprint 3", "state": "active",
                     "startDate": "2026-01-01", "endDate": "2026-01-14", "goal": "Ship"},
                ]
            }
            sprints = jira.list_sprints(board_id=5, state="active")

            assert len(sprints) == 1
            assert sprints[0]["id"] == 42
            assert sprints[0]["goal"] == "Ship"
            call = mock_req.call_args
            assert call[0][0] == "/board/5/sprint"
            assert call[1]["params"]["state"] == "active"

    @patch.dict(os.environ, ENV)
    def test_list_sprints_paginates(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        pages = [
            {"values": [{"id": 1}, {"id": 2}], "isLast": False},
            {"values": [{"id": 3}], "isLast": True},
        ]
        start_ats = []

        def fake(endpoint, params=None, **kwargs):
            start_ats.append(params["startAt"])
            return pages[len(start_ats) - 1]

        with patch.object(jira, "_agile_request", side_effect=fake):
            sprints = jira.list_sprints(board_id=5, state="closed")

        assert [s["id"] for s in sprints] == [1, 2, 3]
        assert start_ats == [0, 2]

    @patch.dict(os.environ, ENV)
    def test_list_sprints_requires_board(self):
        from praisonai_tools import JiraTool

        assert "error" in JiraTool().list_sprints(board_id=None)[0]

    @patch.dict(os.environ, ENV)
    def test_list_sprints_propagates_error(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request", return_value={"error": "boom"}):
            assert jira.list_sprints(board_id=5) == [{"error": "boom"}]

    @patch.dict(os.environ, ENV)
    def test_get_active_sprint(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request") as mock_req:
            mock_req.return_value = {
                "values": [{"id": 42, "name": "Sprint 3", "state": "active"}]
            }
            sprint = jira.get_active_sprint(board_id=5)
            assert sprint["id"] == 42
            assert mock_req.call_args[1]["params"]["state"] == "active"

    @patch.dict(os.environ, ENV)
    def test_get_active_sprint_none(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request", return_value={"values": []}):
            assert jira.get_active_sprint(board_id=5) == {"error": "no active sprint"}

    @patch.dict(os.environ, ENV)
    def test_move_issues_to_sprint(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request") as mock_req:
            mock_req.return_value = {"success": True}
            result = jira.move_issues_to_sprint(sprint_id=42, issue_keys=["P-1", "P-2"])
            assert result == {"success": True, "sprint_id": 42, "moved": 2}
            call = mock_req.call_args
            assert call[0][0] == "/sprint/42/issue"
            assert call[1]["method"] == "POST"
            assert call[1]["data"] == {"issues": ["P-1", "P-2"]}

    @patch.dict(os.environ, ENV)
    def test_move_issues_to_sprint_requires_keys(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request") as mock_req:
            assert "error" in jira.move_issues_to_sprint(sprint_id=42, issue_keys=[])
            mock_req.assert_not_called()

    @patch.dict(os.environ, ENV)
    def test_move_issues_to_sprint_propagates_error(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request", return_value={"error": "403"}):
            assert jira.move_issues_to_sprint(sprint_id=42, issue_keys=["P-1"]) == {"error": "403"}


class TestRunRouting:
    @patch.dict(os.environ, ENV)
    def test_run_list_sprints(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "list_sprints", return_value=[]) as m:
            jira.run(action="list_sprints", board_id=5, state="future")
            m.assert_called_once_with(board_id=5, state="future")

    @patch.dict(os.environ, ENV)
    def test_run_get_active_sprint(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "get_active_sprint", return_value={}) as m:
            jira.run(action="get_active_sprint", board_id=5)
            m.assert_called_once_with(board_id=5)

    @patch.dict(os.environ, ENV)
    def test_run_move_issues_to_sprint(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "move_issues_to_sprint", return_value={}) as m:
            jira.run(action="move-issues-to-sprint", sprint_id=42, issue_keys=["P-1"])
            m.assert_called_once_with(sprint_id=42, issue_keys=["P-1"])


class TestMoveIssuesStringInput:
    @patch.dict(os.environ, ENV)
    def test_move_issues_accepts_comma_string(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request") as mock_req:
            mock_req.return_value = {"success": True}
            result = jira.move_issues_to_sprint(sprint_id=42, issue_keys="PROJ-1, PROJ-2")

            assert result == {"success": True, "sprint_id": 42, "moved": 2}
            assert mock_req.call_args[1]["data"] == {"issues": ["PROJ-1", "PROJ-2"]}
