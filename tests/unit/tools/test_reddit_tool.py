"""Unit tests for RedditTool."""

import os
from unittest.mock import MagicMock, patch

from praisonai_tools.tools.reddit_tool import RedditTool


# ── Import + schema (CI smoke) ──────────────────────────────────────


class TestImportAndSchema:
    def test_import_via_package(self):
        from praisonai_tools import RedditTool as PkgRedditTool

        assert PkgRedditTool is RedditTool

    def test_schema_generation(self):
        tool = RedditTool(client_id="cid", client_secret="secret")
        schema = tool.get_schema()
        assert schema["function"]["name"] == "reddit"
        assert "description" in schema["function"]
        assert "action" in schema["function"]["parameters"]["properties"]


# ── User-Agent ──────────────────────────────────────────────────────


class TestUserAgent:
    def test_default_user_agent_references_app_id(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = RedditTool(client_id="myappid", client_secret="secret")
        assert "myappid" in tool.user_agent

    def test_explicit_user_agent_wins(self):
        tool = RedditTool(client_id="c", client_secret="s", user_agent="custom:ua:1.0")
        assert tool.user_agent == "custom:ua:1.0"

    def test_env_user_agent_used(self):
        with patch.dict(os.environ, {"REDDIT_USER_AGENT": "env:ua:1.0"}, clear=True):
            tool = RedditTool(client_id="c", client_secret="s")
        assert tool.user_agent == "env:ua:1.0"


# ── Write flag gating ───────────────────────────────────────────────


class TestWriteGating:
    def test_write_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = RedditTool(client_id="c", client_secret="s")
        assert tool.allow_write is False

    def test_env_enables_write(self):
        with patch.dict(os.environ, {"REDDIT_ALLOW_WRITE": "1"}, clear=True):
            tool = RedditTool(client_id="c", client_secret="s")
        assert tool.allow_write is True

    def test_post_comment_blocked_when_write_disabled(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = RedditTool(client_id="c", client_secret="s")
        result = tool.post_comment(post_id="abc", body="hi")
        assert "REDDIT_ALLOW_WRITE" in result["error"]

    def test_submit_post_blocked_when_write_disabled(self):
        with patch.dict(os.environ, {}, clear=True):
            tool = RedditTool(client_id="c", client_secret="s")
        result = tool.submit_post(subreddit="test", title="T", body="B")
        assert "REDDIT_ALLOW_WRITE" in result["error"]

    def test_write_requires_account_credentials(self):
        tool = RedditTool(client_id="c", client_secret="s", allow_write=True)
        result = tool.post_comment(post_id="abc", body="hi")
        assert "REDDIT_USERNAME" in result["error"]


# ── Write actions (mocked praw) ─────────────────────────────────────


def _writable_tool():
    return RedditTool(
        client_id="c",
        client_secret="s",
        username="u",
        password="p",
        allow_write=True,
    )


class TestPostComment:
    def test_requires_post_id(self):
        tool = _writable_tool()
        assert tool.post_comment(post_id="", body="hi") == {"error": "post_id is required"}

    def test_requires_body(self):
        tool = _writable_tool()
        assert tool.post_comment(post_id="abc", body="") == {"error": "body is required"}

    def test_success(self):
        tool = _writable_tool()
        comment = MagicMock()
        comment.id = "c1"
        comment.permalink = "/r/test/comments/abc/x/c1/"
        submission = MagicMock()
        submission.reply.return_value = comment
        reddit = MagicMock()
        reddit.submission.return_value = submission
        with patch.object(RedditTool, "reddit", new=reddit):
            result = tool.post_comment(post_id="abc", body="hello")
        submission.reply.assert_called_once_with("hello")
        assert result["success"] is True
        assert result["id"] == "c1"


class TestSubmitPost:
    def test_requires_subreddit(self):
        tool = _writable_tool()
        assert tool.submit_post(subreddit="", title="T") == {"error": "subreddit is required"}

    def test_requires_title(self):
        tool = _writable_tool()
        assert tool.submit_post(subreddit="test", title="") == {"error": "title is required"}

    def test_body_and_url_mutually_exclusive(self):
        tool = _writable_tool()
        result = tool.submit_post(subreddit="test", title="T", body="B", url="http://x")
        assert "not both" in result["error"]

    def test_selftext_success(self):
        tool = _writable_tool()
        submission = MagicMock()
        submission.id = "p1"
        submission.permalink = "/r/test/comments/p1/"
        sub = MagicMock()
        sub.submit.return_value = submission
        reddit = MagicMock()
        reddit.subreddit.return_value = sub
        with patch.object(RedditTool, "reddit", new=reddit):
            result = tool.submit_post(subreddit="test", title="T", body="B")
        sub.submit.assert_called_once_with("T", selftext="B")
        assert result["id"] == "p1"

    def test_link_success(self):
        tool = _writable_tool()
        submission = MagicMock()
        submission.id = "p2"
        submission.permalink = "/r/test/comments/p2/"
        sub = MagicMock()
        sub.submit.return_value = submission
        reddit = MagicMock()
        reddit.subreddit.return_value = sub
        with patch.object(RedditTool, "reddit", new=reddit):
            result = tool.submit_post(subreddit="test", title="T", url="http://x")
        sub.submit.assert_called_once_with("T", url="http://x")
        assert result["id"] == "p2"


# ── run() dispatcher ────────────────────────────────────────────────


class TestRunDispatcher:
    def test_unknown_action(self):
        tool = RedditTool(client_id="c", client_secret="s")
        assert tool.run(action="bogus") == {"error": "Unknown action: bogus"}

    def test_routes_post_comment(self):
        tool = RedditTool(client_id="c", client_secret="s")
        with patch.object(tool, "post_comment", return_value={"ok": True}) as m:
            tool.run(action="post_comment", post_id="abc", body="hi")
        m.assert_called_once_with(post_id="abc", body="hi")

    def test_routes_submit_post(self):
        tool = RedditTool(client_id="c", client_secret="s")
        with patch.object(tool, "submit_post", return_value={"ok": True}) as m:
            tool.run(action="submit-post", subreddit="test", title="T", body="B")
        m.assert_called_once_with(subreddit="test", title="T", body="B", url=None)
