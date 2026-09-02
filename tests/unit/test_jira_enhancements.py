"""Tests for enhanced Jira features (Sprint, Epic, Bulk, Worklog, etc.).

Covers:
- Sprint management (list, active, create, start, complete, move issues)
- Epic operations (list, create, get issues, link)
- Bulk create / bulk transition
- Attachments (list)
- Worklog (log, get)
- Issue links
- Enhanced search with nextPageToken pagination
- Custom fields
- Token masking in errors
"""

import os
from unittest.mock import Mock, patch

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
            assert sprints[0]["state"] == "active"
            call = mock_req.call_args
            assert "/board/5/sprint" in call[0][0]
            assert call[1]["params"]["state"] == "active"

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

    @patch.dict(os.environ, ENV)
    def test_get_active_sprint_none(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request") as mock_req:
            mock_req.return_value = {"values": []}
            sprint = jira.get_active_sprint(board_id=5)
            assert sprint == {"error": "no active sprint"}

    @patch.dict(os.environ, ENV)
    def test_create_sprint(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request") as mock_req:
            mock_req.return_value = {"id": 99, "name": "Sprint 4"}
            result = jira.create_sprint(board_id=5, name="Sprint 4", goal="G")
            assert result["id"] == 99
            call = mock_req.call_args
            assert call[0][0] == "/sprint"
            assert call[1]["method"] == "POST"
            assert call[1]["data"]["originBoardId"] == 5
            assert call[1]["data"]["goal"] == "G"

    @patch.dict(os.environ, ENV)
    def test_start_sprint(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request") as mock_req:
            mock_req.return_value = {"id": 99, "state": "active"}
            jira.start_sprint(sprint_id=99, start_date="2026-01-01", end_date="2026-01-14")
            call = mock_req.call_args
            assert call[1]["data"]["state"] == "active"

    @patch.dict(os.environ, ENV)
    def test_complete_sprint(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request") as mock_req:
            mock_req.return_value = {"id": 99, "state": "closed"}
            jira.complete_sprint(sprint_id=99)
            call = mock_req.call_args
            assert call[1]["data"]["state"] == "closed"

    @patch.dict(os.environ, ENV)
    def test_move_issues_to_sprint(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request") as mock_req:
            mock_req.return_value = {"success": True}
            result = jira.move_issues_to_sprint(sprint_id=42, issue_keys=["P-1", "P-2"])
            assert result["success"] is True
            assert result["moved"] == 2

    @patch.dict(os.environ, ENV)
    def test_move_issues_to_sprint_requires_keys(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        result = jira.move_issues_to_sprint(sprint_id=42, issue_keys=[])
        assert "error" in result

    @patch.dict(os.environ, ENV)
    def test_get_sprint_issues(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request") as mock_req:
            mock_req.return_value = {
                "issues": [
                    {"key": "P-1", "fields": {"summary": "S1", "status": {"name": "To Do"}}}
                ]
            }
            issues = jira.get_sprint_issues(sprint_id=42)
            assert len(issues) == 1
            assert issues[0]["key"] == "P-1"


class TestEpicOperations:
    @patch.dict(os.environ, ENV)
    def test_list_epics(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request") as mock_req:
            mock_req.return_value = {
                "values": [
                    {"id": 10, "key": "P-5", "name": "Auth", "summary": "Auth epic", "done": False}
                ]
            }
            epics = jira.list_epics(board_id=5)
            assert len(epics) == 1
            assert epics[0]["key"] == "P-5"

    @patch.dict(os.environ, ENV)
    def test_create_epic(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_rest_request") as mock_req:
            mock_req.return_value = {"key": "P-9", "id": "1009"}
            result = jira.create_epic(project="P", name="Epic", summary="New epic")
            assert result["success"] is True
            assert result["key"] == "P-9"
            call = mock_req.call_args
            assert call[1]["data"]["fields"]["issuetype"]["name"] == "Epic"

    @patch.dict(os.environ, ENV)
    def test_get_epic_issues(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request") as mock_req:
            mock_req.return_value = {
                "issues": [
                    {"key": "P-1", "fields": {"summary": "S1", "status": {"name": "Done"}}}
                ]
            }
            issues = jira.get_epic_issues(epic_key="P-5")
            assert len(issues) == 1

    @patch.dict(os.environ, ENV)
    def test_link_issue_to_epic(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_agile_request") as mock_req:
            mock_req.return_value = {"success": True}
            result = jira.link_issue_to_epic(epic_key="P-5", issue_keys=["P-1", "P-2"])
            assert result["success"] is True
            assert result["linked"] == 2


class TestBulkOperations:
    @patch.dict(os.environ, ENV)
    def test_bulk_create_issues(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_rest_request") as mock_req:
            mock_req.return_value = {
                "issues": [{"key": "P-1", "id": "1"}, {"key": "P-2", "id": "2"}]
            }
            result = jira.bulk_create_issues(
                issues=[
                    {"project": "P", "summary": "A"},
                    {"project": "P", "summary": "B"},
                ]
            )
            assert len(result) == 2
            assert result[0]["key"] == "P-1"
            call = mock_req.call_args
            assert call[0][0] == "/issue/bulk"

    @patch.dict(os.environ, ENV)
    def test_bulk_create_batches_over_50(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_rest_request") as mock_req:
            mock_req.return_value = {"issues": []}
            jira.bulk_create_issues(
                issues=[{"project": "P", "summary": str(i)} for i in range(120)]
            )
            # 120 issues -> 3 batches (50, 50, 20)
            assert mock_req.call_count == 3

    @patch.dict(os.environ, ENV)
    def test_bulk_transition(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "move_issue") as mock_move:
            mock_move.return_value = {"success": True}
            result = jira.bulk_transition(issue_keys=["P-1", "P-2"], target_status="Done")
            assert result["success"] is True
            assert result["transitioned"] == 2


class TestWorklog:
    @patch.dict(os.environ, ENV)
    def test_log_work(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_rest_request") as mock_req:
            mock_req.return_value = {"id": "100", "timeSpent": "2h 30m"}
            result = jira.log_work(issue_key="P-1", time_spent="2h 30m", comment="done")
            assert result["success"] is True
            assert result["timeSpent"] == "2h 30m"
            call = mock_req.call_args
            assert call[0][0] == "/issue/P-1/worklog"

    @patch.dict(os.environ, ENV)
    def test_get_worklogs(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_rest_request") as mock_req:
            mock_req.return_value = {
                "worklogs": [
                    {"id": "1", "author": {"displayName": "Ann"}, "timeSpent": "1h",
                     "started": "2026-01-01", "comment": "x"}
                ]
            }
            worklogs = jira.get_worklogs(issue_key="P-1")
            assert len(worklogs) == 1
            assert worklogs[0]["author"] == "Ann"


class TestIssueLinks:
    @patch.dict(os.environ, ENV)
    def test_link_issues(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_rest_request") as mock_req:
            mock_req.return_value = {"success": True}
            result = jira.link_issues(outward_issue="P-1", inward_issue="P-2", link_type="blocks")
            assert result["success"] is True
            call = mock_req.call_args
            assert call[0][0] == "/issueLink"
            assert call[1]["data"]["type"]["name"] == "blocks"


class TestEnhancedSearch:
    @patch.dict(os.environ, ENV)
    def test_search_all_paginates(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        pages = [
            {
                "issues": [
                    {"key": "P-1", "fields": {"summary": "A", "status": {"name": "To Do"},
                                              "assignee": {"displayName": "Ann"}}}
                ],
                "nextPageToken": "tok",
            },
            {
                "issues": [
                    {"key": "P-2", "fields": {"summary": "B", "status": {"name": "Done"},
                                              "assignee": None}}
                ],
            },
        ]
        with patch.object(jira, "_rest_request", side_effect=pages) as mock_req:
            issues = jira.search_all(jql="project = P")
            assert len(issues) == 2
            assert issues[0]["assignee"] == "Ann"
            assert issues[1]["assignee"] is None
            assert mock_req.call_count == 2
            # second call must carry the token
            second_call = mock_req.call_args_list[1]
            assert second_call[1]["params"]["nextPageToken"] == "tok"


class TestCustomFields:
    @patch.dict(os.environ, ENV)
    def test_get_custom_fields(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_rest_request") as mock_req:
            mock_req.return_value = [
                {"id": "customfield_1", "name": "Story Points", "custom": True,
                 "schema": {"type": "number"}},
                {"id": "summary", "name": "Summary", "custom": False},
            ]
            fields = jira.get_custom_fields()
            assert len(fields) == 1
            assert fields[0]["id"] == "customfield_1"

    @patch.dict(os.environ, ENV)
    def test_create_issue_with_custom_fields(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_rest_request") as mock_req:
            mock_req.return_value = {"key": "P-10"}
            result = jira.create_issue_with_custom_fields(
                project="P", summary="X", custom_fields={"customfield_1": 5}
            )
            assert result["success"] is True
            call = mock_req.call_args
            assert call[1]["data"]["fields"]["customfield_1"] == 5


class TestTokenMasking:
    @patch.dict(os.environ, ENV)
    def test_mask_hides_token(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        msg = "Auth failed with token super-secret-token in header"
        masked = jira._mask(msg)
        assert "super-secret-token" not in masked
        assert "***" in masked

    @patch.dict(os.environ, ENV)
    def test_rest_request_masks_token_on_error(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        mock_session = Mock()
        mock_session.get.side_effect = Exception("boom super-secret-token")
        jira._session = mock_session

        result = jira._rest_request("/field")
        assert "super-secret-token" not in result["error"]


class TestAttachments:
    @patch.dict(os.environ, ENV)
    def test_list_attachments(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_rest_request") as mock_req:
            mock_req.return_value = {
                "fields": {
                    "attachment": [
                        {"id": "1", "filename": "a.png", "size": 100, "created": "2026"}
                    ]
                }
            }
            attachments = jira.list_attachments(issue_key="P-1")
            assert len(attachments) == 1
            assert attachments[0]["filename"] == "a.png"

    @patch.dict(os.environ, ENV)
    def test_upload_attachment_missing_file(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        result = jira.upload_attachment(issue_key="P-1", file_path="/no/such/file")
        assert "error" in result


class TestWatchers:
    @patch.dict(os.environ, ENV)
    def test_add_watcher(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "_rest_request") as mock_req:
            mock_req.return_value = {"success": True}
            result = jira.add_watcher(issue_key="P-1", account_id="acc-123")
            assert result["success"] is True


class TestRunRouting:
    @patch.dict(os.environ, ENV)
    def test_run_list_sprints(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "list_sprints") as mock_method:
            mock_method.return_value = []
            jira.run(action="list_sprints", board_id=5, state="future")
            mock_method.assert_called_once_with(board_id=5, state="future")

    @patch.dict(os.environ, ENV)
    def test_run_log_work(self):
        from praisonai_tools import JiraTool

        jira = JiraTool()
        with patch.object(jira, "log_work") as mock_method:
            mock_method.return_value = {"success": True}
            jira.run(action="log_work", issue_key="P-1", time_spent="1h")
            mock_method.assert_called_once()


class TestStandaloneFunctions:
    @patch.dict(os.environ, ENV)
    def test_jira_list_sprints_function(self):
        from praisonai_tools import jira_list_sprints

        with patch("praisonai_tools.tools.jira_tool.JiraTool.list_sprints") as mock_method:
            mock_method.return_value = [{"id": 1}]
            result = jira_list_sprints(board_id=5)
            assert len(result) == 1

    @patch.dict(os.environ, ENV)
    def test_jira_search_all_function(self):
        from praisonai_tools import jira_search_all

        with patch("praisonai_tools.tools.jira_tool.JiraTool.search_all") as mock_method:
            mock_method.return_value = [{"key": "P-1"}]
            result = jira_search_all(jql="project = P")
            assert len(result) == 1
