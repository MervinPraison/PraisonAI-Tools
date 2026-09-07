"""Unit tests for NotionTool and AsyncNotionTool."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from praisonai_tools.tools.notion_tool import (
    AsyncNotionTool,
    NotionTool,
    blocks_to_markdown,
    bulleted_list,
    callout,
    code_block,
    divider,
    heading,
    markdown_to_blocks,
    paragraph,
    table,
    todo,
)


def _mock_response(payload, status_code=200, headers=None):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.status_code = status_code
    resp.headers = headers or {}
    return resp


# ── Init / validation ───────────────────────────────────────────────


class TestInit:
    def test_default_api_version(self):
        tool = NotionTool(api_key="x")
        assert tool.api_version == "2026-03-11"

    def test_custom_api_version(self):
        tool = NotionTool(api_key="x", api_version="2022-06-28")
        assert tool.api_version == "2022-06-28"

    def test_validate_raises_without_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="NOTION_API_KEY is required"):
                NotionTool(validate=True)

    def test_headers_include_auth_and_version(self):
        tool = NotionTool(api_key="secret")
        headers = tool._headers()
        assert headers["Authorization"] == "Bearer secret"
        assert headers["Notion-Version"] == "2026-03-11"


# ── _request ────────────────────────────────────────────────────────


class TestRequest:
    def test_missing_key_returns_error(self):
        with patch.dict("os.environ", {}, clear=True):
            tool = NotionTool()
            assert tool._request("GET", "users") == {"error": "NOTION_API_KEY not configured"}

    def test_http_error_returns_message(self):
        tool = NotionTool(api_key="x")
        resp = _mock_response({"message": "Not found"}, status_code=404)
        with patch("requests.get", return_value=resp):
            assert tool._request("GET", "pages/1") == {"error": "Not found"}

    def test_retries_on_429_then_succeeds(self):
        tool = NotionTool(api_key="x")
        r429 = _mock_response({}, status_code=429, headers={"Retry-After": "0"})
        ok = _mock_response({"ok": True}, status_code=200)
        with patch("requests.get", side_effect=[r429, ok]), patch("time.sleep"):
            assert tool._request("GET", "pages/1") == {"ok": True}


# ── Block builders ──────────────────────────────────────────────────


class TestBlockBuilders:
    def test_heading_clamps_level(self):
        assert heading("t", 5)["type"] == "heading_3"
        assert heading("t", 0)["type"] == "heading_1"

    def test_paragraph(self):
        block = paragraph("hello")
        assert block["paragraph"]["rich_text"][0]["text"]["content"] == "hello"

    def test_bulleted_list(self):
        blocks = bulleted_list(["a", "b"])
        assert len(blocks) == 2
        assert blocks[0]["type"] == "bulleted_list_item"

    def test_todo_checked(self):
        block = todo("do", checked=True)
        assert block["to_do"]["checked"] is True

    def test_code_block(self):
        block = code_block("print(1)", "python")
        assert block["code"]["language"] == "python"

    def test_divider(self):
        assert divider()["type"] == "divider"

    def test_callout(self):
        block = callout("note", "🔥")
        assert block["callout"]["icon"]["emoji"] == "🔥"

    def test_table(self):
        block = table([["a", "b"], ["1", "2"]])
        assert block["table"]["table_width"] == 2
        assert len(block["table"]["children"]) == 2


# ── Markdown conversion ─────────────────────────────────────────────


class TestMarkdownConversion:
    def test_headings(self):
        blocks = markdown_to_blocks("# H1\n## H2\n### H3")
        assert [b["type"] for b in blocks] == ["heading_1", "heading_2", "heading_3"]

    def test_bullets_and_numbers(self):
        blocks = markdown_to_blocks("- a\n1. b")
        assert blocks[0]["type"] == "bulleted_list_item"
        assert blocks[1]["type"] == "numbered_list_item"

    def test_todo(self):
        blocks = markdown_to_blocks("- [x] done\n- [ ] pending")
        assert blocks[0]["to_do"]["checked"] is True
        assert blocks[1]["to_do"]["checked"] is False

    def test_code_fence(self):
        blocks = markdown_to_blocks("```python\nprint(1)\n```")
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["rich_text"][0]["text"]["content"] == "print(1)"

    def test_divider_and_paragraph(self):
        blocks = markdown_to_blocks("---\nhello world")
        assert blocks[0]["type"] == "divider"
        assert blocks[1]["type"] == "paragraph"

    def test_roundtrip_basic(self):
        md = "# Title\n\n- one\n\n- two"
        blocks = markdown_to_blocks(md)
        out = blocks_to_markdown(blocks)
        assert "# Title" in out
        assert "- one" in out
        assert "- two" in out

    def test_blocks_to_markdown_todo_and_code(self):
        blocks = [
            todo("task", checked=True),
            code_block("x=1", "python"),
        ]
        md = blocks_to_markdown(blocks)
        assert "- [x] task" in md
        assert "```python" in md


# ── Blocks API ──────────────────────────────────────────────────────


class TestGetBlockChildren:
    def test_requires_block_id(self):
        tool = NotionTool(api_key="x")
        assert tool.get_block_children(block_id="") == [{"error": "block_id is required"}]

    def test_paginates(self):
        tool = NotionTool(api_key="x")
        page1 = _mock_response(
            {"results": [{"id": "b1"}], "has_more": True, "next_cursor": "c2"}
        )
        page2 = _mock_response({"results": [{"id": "b2"}], "has_more": False})
        with patch("requests.get", side_effect=[page1, page2]):
            blocks = tool.get_block_children("page1")
        assert [b["id"] for b in blocks] == ["b1", "b2"]


class TestGetPageContent:
    def test_returns_markdown(self):
        tool = NotionTool(api_key="x")
        payload = {
            "results": [
                {"type": "heading_1", "heading_1": {"rich_text": [{"plain_text": "T"}]}},
                {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "body"}]}},
            ],
            "has_more": False,
        }
        with patch("requests.get", return_value=_mock_response(payload)):
            md = tool.get_page_content("page1")
        assert md == "# T\n\nbody"

    def test_returns_blocks_when_not_markdown(self):
        tool = NotionTool(api_key="x")
        payload = {"results": [{"type": "paragraph", "paragraph": {"rich_text": []}}],
                   "has_more": False}
        with patch("requests.get", return_value=_mock_response(payload)):
            blocks = tool.get_page_content("page1", as_markdown=False)
        assert isinstance(blocks, list)


class TestAppendBlocks:
    def test_requires_block_id(self):
        tool = NotionTool(api_key="x")
        assert tool.append_blocks(block_id="", blocks=[paragraph("x")]) == {
            "error": "block_id is required"
        }

    def test_requires_blocks(self):
        tool = NotionTool(api_key="x")
        assert tool.append_blocks(block_id="b1", blocks=[]) == {"error": "blocks is required"}

    def test_success(self):
        tool = NotionTool(api_key="x")
        resp = _mock_response({"results": [{"id": "b1"}, {"id": "b2"}]})
        with patch("requests.patch", return_value=resp) as p:
            result = tool.append_blocks("page1", [paragraph("a"), paragraph("b")])
        assert result == {"success": True, "appended": 2}
        assert p.call_args.kwargs["json"] == {"children": [paragraph("a"), paragraph("b")]}


class TestUpdateDeleteBlock:
    def test_update_requires_id(self):
        tool = NotionTool(api_key="x")
        assert tool.update_block(block_id="", block_data={"x": 1}) == {
            "error": "block_id is required"
        }

    def test_update_success(self):
        tool = NotionTool(api_key="x")
        with patch("requests.patch", return_value=_mock_response({"id": "b1"})):
            assert tool.update_block("b1", paragraph("new")) == {"success": True, "id": "b1"}

    def test_delete_success(self):
        tool = NotionTool(api_key="x")
        with patch("requests.delete", return_value=_mock_response({"id": "b1"})):
            assert tool.delete_block("b1") == {
                "success": True,
                "id": "b1",
                "archived": True,
            }


# ── Pages (write) ───────────────────────────────────────────────────


class TestUpdatePage:
    def test_requires_page_id(self):
        tool = NotionTool(api_key="x")
        assert tool.update_page(page_id="") == {"error": "page_id is required"}

    def test_requires_properties_or_archive(self):
        tool = NotionTool(api_key="x")
        assert tool.update_page(page_id="p1") == {
            "error": "properties or archived is required"
        }

    def test_archive(self):
        tool = NotionTool(api_key="x")
        with patch("requests.patch", return_value=_mock_response({"id": "p1", "archived": True})) as p:
            result = tool.update_page("p1", archived=True)
        assert result == {"success": True, "id": "p1", "archived": True}
        assert p.call_args.kwargs["json"] == {"archived": True}


class TestCreatePageRich:
    def test_from_markdown(self):
        tool = NotionTool(api_key="x")
        resp = _mock_response({"id": "p1", "url": "http://n/p1"})
        with patch("requests.post", return_value=resp) as p:
            result = tool.create_page_rich("parent1", "Title", markdown="# Hello\n- a")
        assert result == {"success": True, "id": "p1", "url": "http://n/p1"}
        children = p.call_args.kwargs["json"]["children"]
        assert children[0]["type"] == "heading_1"
        assert children[1]["type"] == "bulleted_list_item"

    def test_requires_parent(self):
        tool = NotionTool(api_key="x")
        assert tool.create_page_rich(parent_id="", title="T") == {
            "error": "parent_id is required"
        }


# ── Databases ───────────────────────────────────────────────────────


class TestQueryDatabaseAll:
    def test_paginates_all_rows(self):
        tool = NotionTool(api_key="x")
        row1 = {"id": "r1", "properties": {"Name": {"type": "title",
                "title": [{"plain_text": "One"}]}}}
        row2 = {"id": "r2", "properties": {"Name": {"type": "title",
                "title": [{"plain_text": "Two"}]}}}
        page1 = _mock_response({"results": [row1], "has_more": True, "next_cursor": "c2"})
        page2 = _mock_response({"results": [row2], "has_more": False})
        with patch("requests.post", side_effect=[page1, page2]):
            rows = tool.query_database_all("db1")
        assert [r["Name"] for r in rows] == ["One", "Two"]

    def test_requires_database_id(self):
        tool = NotionTool(api_key="x")
        assert tool.query_database_all(database_id="") == [
            {"error": "database_id is required"}
        ]


class TestCreateUpdateDatabase:
    def test_create_requires_fields(self):
        tool = NotionTool(api_key="x")
        assert tool.create_database(parent_page_id="", title="T", properties={"Name": {}}) == {
            "error": "parent_page_id is required"
        }

    def test_create_success(self):
        tool = NotionTool(api_key="x")
        resp = _mock_response({"id": "db1", "url": "http://n/db1"})
        with patch("requests.post", return_value=resp) as p:
            result = tool.create_database("page1", "DB", {"Name": {"title": {}}})
        assert result == {"success": True, "id": "db1", "url": "http://n/db1"}
        sent = p.call_args.kwargs["json"]
        assert sent["parent"] == {"type": "page_id", "page_id": "page1"}

    def test_update_requires_something(self):
        tool = NotionTool(api_key="x")
        assert tool.update_database(database_id="db1") == {
            "error": "title or properties is required"
        }

    def test_update_title(self):
        tool = NotionTool(api_key="x")
        with patch("requests.patch", return_value=_mock_response({"id": "db1"})):
            assert tool.update_database("db1", title="New") == {"success": True, "id": "db1"}


# ── Users ───────────────────────────────────────────────────────────


class TestUsers:
    def test_list_users(self):
        tool = NotionTool(api_key="x")
        payload = {
            "results": [
                {"id": "u1", "name": "Alice", "type": "person",
                 "person": {"email": "a@x.com"}},
                {"id": "u2", "name": "Bot", "type": "bot"},
            ],
            "has_more": False,
        }
        with patch("requests.get", return_value=_mock_response(payload)):
            users = tool.list_users()
        assert users[0]["email"] == "a@x.com"
        assert users[1]["email"] is None

    def test_get_user_requires_id(self):
        tool = NotionTool(api_key="x")
        assert tool.get_user(user_id="") == {"error": "user_id is required"}

    def test_get_user(self):
        tool = NotionTool(api_key="x")
        payload = {"id": "u1", "name": "Alice", "type": "person",
                   "person": {"email": "a@x.com"}}
        with patch("requests.get", return_value=_mock_response(payload)):
            user = tool.get_user("u1")
        assert user["name"] == "Alice"


# ── run() dispatcher ────────────────────────────────────────────────


class TestRunDispatcher:
    def test_unknown_action(self):
        tool = NotionTool(api_key="x")
        assert tool.run(action="bogus") == {"error": "Unknown action: bogus"}

    def test_routes_get_page_content(self):
        tool = NotionTool(api_key="x")
        with patch.object(tool, "get_page_content", return_value="md") as m:
            out = tool.run(action="get_page_content", page_id="p1")
        m.assert_called_once_with(page_id="p1")
        assert out == "md"

    def test_routes_append_blocks_with_block_id_fallback(self):
        tool = NotionTool(api_key="x")
        with patch.object(tool, "append_blocks", return_value={"ok": True}) as m:
            tool.run(action="append-blocks", page_id="p1", blocks=[paragraph("x")])
        m.assert_called_once_with(block_id="p1", blocks=[paragraph("x")])


# ── Async ───────────────────────────────────────────────────────────


class TestAsyncNotionTool:
    def test_get_page_content_async(self):
        tool = AsyncNotionTool(api_key="x")
        payload = {
            "results": [
                {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "hi"}]}}
            ],
            "has_more": False,
        }

        class _Resp:
            status_code = 200
            headers = {}

            def json(self):
                return payload

        class _Client:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, *a, **k):
                return _Resp()

        with patch("httpx.AsyncClient", return_value=_Client()):
            md = asyncio.run(tool.get_page_content("page1"))
        assert md == "hi"
