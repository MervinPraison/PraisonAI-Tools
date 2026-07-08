"""Unit tests for JIRA watch tools."""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Optional dependency — stub so @patch("jira.JIRA") resolves in CI without jira installed.
sys.modules.setdefault("jira", MagicMock())

from praisonai_tools.tools.jira_watch_tool import (  # noqa: E402
    jira_watch_issue,
    jira_watch_project,
    jira_get_issue_info,
    jira_search_issues,
    jira_tools,
    _get_jira_connection,
    _validate_project_key,
)


class TestJIRAConnection:
    @patch("jira.JIRA")
    def test_connection_with_email_token(self, mock_jira):
        _get_jira_connection(
            url="https://test.atlassian.net",
            email="test@example.com",
            token="test_token",
        )
        mock_jira.assert_called_once_with(
            server="https://test.atlassian.net",
            basic_auth=("test@example.com", "test_token"),
        )

    @patch("jira.JIRA")
    def test_connection_with_username_token(self, mock_jira):
        _get_jira_connection(
            url="https://test.atlassian.net",
            username="test_user",
            token="test_token",
        )
        mock_jira.assert_called_once_with(
            server="https://test.atlassian.net",
            basic_auth=("test_user", "test_token"),
        )

    def test_connection_missing_auth(self):
        with pytest.raises(ValueError, match="JIRA authentication required"):
            _get_jira_connection(url="https://test.atlassian.net")

    def test_connection_missing_url(self):
        with pytest.raises(ValueError, match="JIRA URL is required"):
            _get_jira_connection(email="test@example.com", token="token")


class TestJIRAGetIssueInfo:
    @patch("praisonai_tools.tools.jira_watch_tool._get_jira_connection")
    def test_get_issue_info_success(self, mock_connection):
        mock_jira = Mock()
        mock_connection.return_value = mock_jira

        mock_issue = Mock()
        mock_issue.key = "PROJ-123"
        mock_issue.fields.summary = "Test issue"
        mock_issue.fields.status.name = "Open"
        mock_issue.fields.priority.name = "High"
        mock_issue.fields.assignee.displayName = "John Doe"
        mock_issue.fields.reporter.displayName = "Jane Smith"
        mock_issue.fields.created = "2024-01-01T10:00:00"
        mock_issue.fields.updated = "2024-01-02T15:30:00"
        mock_issue.fields.description = "Test description"

        mock_jira.issue.return_value = mock_issue
        mock_jira.comments.return_value = []

        result = jira_get_issue_info(
            issue_key="PROJ-123",
            url="https://test.atlassian.net",
            email="test@example.com",
            token="test_token",
        )

        assert "PROJ-123" in result
        assert "Test issue" in result
        assert "Open" in result


class TestJIRASearchIssues:
    @patch("praisonai_tools.tools.jira_watch_tool._get_jira_connection")
    def test_search_issues_success(self, mock_connection):
        mock_jira = Mock()
        mock_connection.return_value = mock_jira

        mock_issue = Mock()
        mock_issue.key = "PROJ-123"
        mock_issue.fields.summary = "First issue"
        mock_issue.fields.status.name = "Open"
        mock_issue.fields.assignee.displayName = "John Doe"
        mock_issue.fields.updated = "2024-01-01T10:00:00"

        mock_jira.search_issues.return_value = [mock_issue]

        result = jira_search_issues(
            jql="project = PROJ",
            url="https://test.atlassian.net",
            email="test@example.com",
            token="test_token",
        )

        assert "Found 1 issues" in result
        assert "PROJ-123" in result


class TestJIRAWatchIssue:
    @patch("praisonai_tools.tools.jira_watch_tool._get_jira_connection")
    def test_watch_issue_current_state(self, mock_connection):
        mock_jira = Mock()
        mock_connection.return_value = mock_jira

        mock_issue = Mock()
        mock_issue.fields.updated = "2024-01-01T10:00:00"
        mock_issue.fields.status.name = "Open"
        mock_issue.fields.summary = "Test issue"
        mock_issue.fields.assignee.displayName = "John Doe"
        mock_issue.fields.priority.name = "High"

        mock_jira.issue.return_value = mock_issue

        result = jira_watch_issue(
            issue_key="PROJ-123",
            url="https://test.atlassian.net",
            email="test@example.com",
            token="test_token",
        )

        assert "current state" in result
        assert "PROJ-123" in result


class TestJIRAWatchProject:
    @patch("praisonai_tools.tools.jira_watch_tool._get_jira_connection")
    def test_watch_project_recent_activity(self, mock_connection):
        mock_jira = Mock()
        mock_connection.return_value = mock_jira

        mock_issue = Mock()
        mock_issue.key = "PROJ-123"
        mock_issue.fields.summary = "Test issue"
        mock_issue.fields.status.name = "Open"
        mock_issue.fields.updated = "2024-01-01T10:00:00"

        mock_jira.search_issues.return_value = [mock_issue]

        result = jira_watch_project(
            project_key="PROJ",
            url="https://test.atlassian.net",
            email="test@example.com",
            token="test_token",
        )

        assert "recent activity" in result
        assert "PROJ-123" in result


class TestJIRAValidation:
    def test_validate_project_key_valid(self):
        assert _validate_project_key("PROJ")
        assert _validate_project_key("MY_PROJECT")

    def test_validate_project_key_invalid(self):
        with pytest.raises(ValueError):
            _validate_project_key("proj")
        with pytest.raises(ValueError):
            _validate_project_key("PROJ OR 1=1")


def test_jira_tools_collection():
    tools = jira_tools()
    assert isinstance(tools, list)
    assert len(tools) == 4
