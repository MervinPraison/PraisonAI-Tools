"""Unit tests for the Google Workspace tools slice.

These tests avoid any network / real Google calls. They exercise:
- shared auth scope resolution and mode selection,
- the webhook path that needs no auth,
- tool method wiring against a mocked service,
- auto-discovery of the new tool classes.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from praisonai_tools.tools._google_auth import GoogleWorkspaceAuth, resolve_auth
from praisonai_tools.tools.google_docs_tool import GoogleDocsTool
from praisonai_tools.tools.google_tasks_tool import GoogleTasksTool
from praisonai_tools.tools.google_chat_tool import GoogleChatTool
from praisonai_tools.tools.google_slides_tool import GoogleSlidesTool


# ── Shared auth ─────────────────────────────────────────────────────


class TestGoogleWorkspaceAuth:
    def test_scopes_combined_and_deduped(self):
        auth = GoogleWorkspaceAuth()
        scopes = auth.scopes_for(["docs", "drive", "docs"])
        assert "https://www.googleapis.com/auth/documents" in scopes
        assert "https://www.googleapis.com/auth/drive" in scopes
        assert len(scopes) == len(set(scopes))

    def test_unknown_service_raises(self):
        with pytest.raises(ValueError):
            GoogleWorkspaceAuth().scopes_for(["not_a_service"])

    def test_no_services_raises(self):
        with pytest.raises(ValueError):
            GoogleWorkspaceAuth().scopes_for([])

    def test_service_account_mode_selected_when_file_set(self, tmp_path):
        sa_file = tmp_path / "sa.json"
        sa_file.write_text("{}")
        auth = GoogleWorkspaceAuth(
            services=["docs"], service_account_file=str(sa_file)
        )
        with patch.object(
            auth, "_service_account_credentials", return_value="SA"
        ) as sa:
            creds = auth.get_credentials()
        assert creds == "SA"
        sa.assert_called_once()

    def test_oauth_mode_selected_when_token_exists(self, tmp_path):
        token = tmp_path / "token.json"
        token.write_text("{}")
        with patch.dict(os.environ, {}, clear=True):
            auth = GoogleWorkspaceAuth(
                services=["docs"], token_file=str(token)
            )
        with patch.object(auth, "_oauth_credentials", return_value="OAUTH") as oa:
            creds = auth.get_credentials()
        assert creds == "OAUTH"
        oa.assert_called_once()

    def test_adc_mode_when_nothing_configured(self, tmp_path):
        missing_token = tmp_path / "nope.json"
        with patch.dict(os.environ, {}, clear=True):
            auth = GoogleWorkspaceAuth(
                services=["docs"],
                credentials_file=str(tmp_path / "missing_creds.json"),
                token_file=str(missing_token),
            )
        with patch.object(auth, "_default_credentials", return_value="ADC") as adc:
            creds = auth.get_credentials()
        assert creds == "ADC"
        adc.assert_called_once()

    def test_credentials_cached(self, tmp_path):
        auth = GoogleWorkspaceAuth(
            services=["docs"],
            credentials_file=str(tmp_path / "missing.json"),
            token_file=str(tmp_path / "missing_token.json"),
        )
        with patch.object(
            auth, "_default_credentials", return_value="ADC"
        ) as adc:
            auth.get_credentials()
            auth.get_credentials()
        adc.assert_called_once()

    def test_resolve_auth_reuses_provided(self):
        shared = GoogleWorkspaceAuth(services=["docs"])
        assert resolve_auth(shared, ["docs"]) is shared

    def test_resolve_auth_builds_when_none(self):
        auth = resolve_auth(None, ["tasks"])
        assert isinstance(auth, GoogleWorkspaceAuth)
        assert auth.services == ["tasks"]


# ── Tools accept a shared auth ──────────────────────────────────────


class TestSharedAuthWiring:
    def test_tools_reuse_shared_auth(self):
        shared = GoogleWorkspaceAuth(services=["docs", "tasks", "chat", "slides"])
        assert GoogleDocsTool(auth=shared)._auth is shared
        assert GoogleTasksTool(auth=shared)._auth is shared
        assert GoogleChatTool(auth=shared)._auth is shared
        assert GoogleSlidesTool(auth=shared)._auth is shared


# ── Docs ────────────────────────────────────────────────────────────


class TestGoogleDocsTool:
    def test_create_document(self):
        tool = GoogleDocsTool(auth=GoogleWorkspaceAuth(services=["docs"]))
        mock = MagicMock()
        mock.documents().create().execute.return_value = {
            "documentId": "abc",
            "title": "T",
        }
        tool._docs = mock
        result = tool.create_document("T")
        assert result["success"] is True
        assert result["document_id"] == "abc"

    def test_create_document_requires_title(self):
        tool = GoogleDocsTool(auth=GoogleWorkspaceAuth(services=["docs"]))
        assert "error" in tool.create_document("")

    def test_read_document_text(self):
        tool = GoogleDocsTool(auth=GoogleWorkspaceAuth(services=["docs"]))
        mock = MagicMock()
        mock.documents().get().execute.return_value = {
            "body": {
                "content": [
                    {"paragraph": {"elements": [{"textRun": {"content": "Hello "}}]}},
                    {"paragraph": {"elements": [{"textRun": {"content": "world"}}]}},
                ]
            }
        }
        tool._docs = mock
        assert tool.read_document_text("abc") == "Hello world"


# ── Tasks ───────────────────────────────────────────────────────────


class TestGoogleTasksTool:
    def test_list_task_lists(self):
        tool = GoogleTasksTool(auth=GoogleWorkspaceAuth(services=["tasks"]))
        mock = MagicMock()
        mock.tasklists().list().execute.return_value = {
            "items": [{"id": "l1", "title": "My List"}]
        }
        tool._service = mock
        lists = tool.list_task_lists()
        assert lists == [{"id": "l1", "title": "My List"}]

    def test_create_task_requires_args(self):
        tool = GoogleTasksTool(auth=GoogleWorkspaceAuth(services=["tasks"]))
        assert "error" in tool.create_task("", "")

    def test_complete_task(self):
        tool = GoogleTasksTool(auth=GoogleWorkspaceAuth(services=["tasks"]))
        mock = MagicMock()
        mock.tasks().patch().execute.return_value = {
            "id": "t1",
            "status": "completed",
        }
        tool._service = mock
        result = tool.complete_task("l1", "t1")
        assert result["status"] == "completed"


# ── Chat (webhook needs no auth) ────────────────────────────────────


class TestGoogleChatTool:
    def test_webhook_no_auth(self):
        tool = GoogleChatTool(auth=GoogleWorkspaceAuth(services=["chat"]))
        fake_resp = MagicMock()
        fake_resp.getcode.return_value = 200
        fake_resp.__enter__.return_value = fake_resp
        fake_resp.__exit__.return_value = False
        with patch("urllib.request.urlopen", return_value=fake_resp) as urlopen:
            result = tool.create_webhook_message("https://chat.example/x", "hi")
        assert result["success"] is True
        assert result["status"] == 200
        urlopen.assert_called_once()

    def test_webhook_requires_url(self):
        tool = GoogleChatTool(auth=GoogleWorkspaceAuth(services=["chat"]))
        assert "error" in tool.create_webhook_message("", "hi")

    def test_send_message(self):
        tool = GoogleChatTool(auth=GoogleWorkspaceAuth(services=["chat"]))
        mock = MagicMock()
        mock.spaces().messages().create().execute.return_value = {
            "name": "spaces/x/messages/1"
        }
        tool._service = mock
        result = tool.send_message("spaces/x", "hello")
        assert result["success"] is True


# ── Slides ──────────────────────────────────────────────────────────


class TestGoogleSlidesTool:
    def test_create_presentation(self):
        tool = GoogleSlidesTool(auth=GoogleWorkspaceAuth(services=["slides"]))
        mock = MagicMock()
        mock.presentations().create().execute.return_value = {
            "presentationId": "p1",
            "title": "Deck",
        }
        tool._slides = mock
        result = tool.create_presentation("Deck")
        assert result["presentation_id"] == "p1"

    def test_add_slide(self):
        tool = GoogleSlidesTool(auth=GoogleWorkspaceAuth(services=["slides"]))
        mock = MagicMock()
        mock.presentations().batchUpdate().execute.return_value = {}
        tool._slides = mock
        result = tool.add_slide("p1")
        assert result["success"] is True
        assert result["slide_id"].startswith("slide_")


# ── Existing tools accept shared auth (backward compatible) ─────────


class TestExistingToolsAcceptAuth:
    """The four pre-existing Google tools opt into the shared auth via auth=."""

    def _assert_uses_shared_auth(self, tool, api, version, service):
        auth = MagicMock()
        auth.build_service.return_value = "SVC"
        tool.auth = auth
        tool._service = None
        assert tool.service == "SVC"
        auth.build_service.assert_called_once_with(api, version, [service])

    def test_gmail_uses_shared_auth(self):
        from praisonai_tools.tools.gmail_tool import GmailTool

        auth = MagicMock()
        auth.build_service.return_value = "SVC"
        tool = GmailTool(auth=auth)
        assert tool.service == "SVC"
        auth.build_service.assert_called_once_with("gmail", "v1", ["gmail"])

    def test_drive_uses_shared_auth(self):
        from praisonai_tools.tools.google_drive_tool import GoogleDriveTool

        auth = MagicMock()
        auth.build_service.return_value = "SVC"
        tool = GoogleDriveTool(auth=auth)
        assert tool.service == "SVC"
        auth.build_service.assert_called_once_with("drive", "v3", ["drive"])

    def test_calendar_uses_shared_auth(self):
        from praisonai_tools.tools.google_calendar_tool import GoogleCalendarTool

        auth = MagicMock()
        auth.build_service.return_value = "SVC"
        tool = GoogleCalendarTool(auth=auth)
        assert tool.service == "SVC"
        auth.build_service.assert_called_once_with("calendar", "v3", ["calendar"])

    def test_sheets_uses_shared_auth(self):
        from praisonai_tools.tools.google_sheets_tool import GoogleSheetsTool

        auth = MagicMock()
        auth.build_service.return_value = "SVC"
        tool = GoogleSheetsTool(auth=auth)
        assert tool.service == "SVC"
        auth.build_service.assert_called_once_with("sheets", "v4", ["sheets"])

    def test_legacy_construction_still_works(self):
        from praisonai_tools.tools.gmail_tool import GmailTool
        from praisonai_tools.tools.google_drive_tool import GoogleDriveTool
        from praisonai_tools.tools.google_calendar_tool import GoogleCalendarTool
        from praisonai_tools.tools.google_sheets_tool import GoogleSheetsTool

        for cls in (GmailTool, GoogleDriveTool, GoogleCalendarTool, GoogleSheetsTool):
            assert cls().auth is None


# ── Discovery ───────────────────────────────────────────────────────


class TestDiscovery:
    def test_new_tools_discoverable(self):
        import praisonai_tools.tools as tools_pkg

        for name in (
            "GoogleDocsTool",
            "GoogleTasksTool",
            "GoogleChatTool",
            "GoogleSlidesTool",
        ):
            assert name in tools_pkg.__all__, f"{name} not auto-discovered"
            assert getattr(tools_pkg, name) is not None
