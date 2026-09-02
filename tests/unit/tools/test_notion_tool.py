"""Unit tests for NotionTool (blocks, pagination, markdown, page/db updates)."""

from unittest.mock import MagicMock, patch

from praisonai_tools.tools.notion_tool import (
    NotionTool,
    bulleted_list,
    callout,
    code_block,
    divider,
    heading,
    numbered_list,
    paragraph,
    todo,
)


def _mock_response(payload, status=200):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.status_code = status
    return resp


# ── get_block_children / pagination ─────────────────────────────────


class TestGetBlockChildren:
    def test_requires_block_id(self):
        tool = NotionTool(api_key="x")
        assert tool.get_block_children(block_id="") == [
            {"error": "block_id is required"}
        ]

    def test_paginates_across_cursors(self):
        tool = NotionTool(api_key="x")
        page1 = {
            "results": [{"id": "b1", "type": "paragraph"}],
            "has_more": True,
            "next_cursor": "cur2",
        }
        page2 = {
            "results": [{"id": "b2", "type": "paragraph"}],
            "has_more": False,
            "next_cursor": None,
        }
        with patch(
            "requests.get",
            side_effect=[_mock_response(page1), _mock_response(page2)],
        ) as get:
            blocks = tool.get_block_children(block_id="page1")

        assert [b["id"] for b in blocks] == ["b1", "b2"]
        # second call must carry the cursor
        assert get.call_args_list[1].kwargs["params"]["start_cursor"] == "cur2"

    def test_recursive_fetches_children(self):
        tool = NotionTool(api_key="x")
        parent = {
            "results": [{"id": "b1", "type": "paragraph", "has_children": True}],
            "has_more": False,
        }
        child = {
            "results": [{"id": "b1a", "type": "paragraph"}],
            "has_more": False,
        }
        with patch(
            "requests.get",
            side_effect=[_mock_response(parent), _mock_response(child)],
        ):
            blocks = tool.get_block_children(block_id="page1", recursive=True)

        assert blocks[0]["_children"][0]["id"] == "b1a"

    def test_propagates_error(self):
        tool = NotionTool(api_key="x")
        with patch("requests.get", side_effect=RuntimeError("net")):
            assert tool.get_block_children(block_id="p") == [{"error": "net"}]


# ── get_page_content → markdown ─────────────────────────────────────


class TestGetPageContent:
    def test_returns_markdown(self):
        tool = NotionTool(api_key="x")
        payload = {
            "results": [
                {
                    "id": "h",
                    "type": "heading_1",
                    "heading_1": {"rich_text": [{"plain_text": "Title"}]},
                },
                {
                    "id": "p",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"plain_text": "Body"}]},
                },
            ],
            "has_more": False,
        }
        with patch("requests.get", return_value=_mock_response(payload)):
            md = tool.get_page_content(page_id="p1")
        assert md == "# Title\nBody"

    def test_as_blocks(self):
        tool = NotionTool(api_key="x")
        payload = {"results": [{"id": "p", "type": "paragraph"}], "has_more": False}
        with patch("requests.get", return_value=_mock_response(payload)):
            blocks = tool.get_page_content(page_id="p1", as_markdown=False)
        assert blocks[0]["id"] == "p"


# ── append_blocks ───────────────────────────────────────────────────


class TestAppendBlocks:
    def test_requires_block_id(self):
        tool = NotionTool(api_key="x")
        assert tool.append_blocks(block_id="", blocks=[{}]) == {
            "error": "block_id is required"
        }

    def test_requires_blocks(self):
        tool = NotionTool(api_key="x")
        assert tool.append_blocks(block_id="b1", blocks=[]) == {
            "error": "blocks is required"
        }

    def test_success_sends_children(self):
        tool = NotionTool(api_key="x")
        blocks = [paragraph("hi")]
        with patch(
            "requests.patch",
            return_value=_mock_response({"results": [{"id": "n1"}]}),
        ) as patch_req:
            result = tool.append_blocks(block_id="b1", blocks=blocks)

        assert patch_req.call_args.kwargs["json"] == {"children": blocks}
        assert result["success"] is True


# ── delete_block / update_page ──────────────────────────────────────


class TestDeleteBlock:
    def test_requires_block_id(self):
        tool = NotionTool(api_key="x")
        assert tool.delete_block(block_id="") == {"error": "block_id is required"}

    def test_success(self):
        tool = NotionTool(api_key="x")
        with patch("requests.delete", return_value=_mock_response({"id": "b1"})):
            assert tool.delete_block(block_id="b1") == {"success": True, "id": "b1"}


class TestUpdatePage:
    def test_requires_page_id(self):
        tool = NotionTool(api_key="x")
        assert tool.update_page(page_id="") == {"error": "page_id is required"}

    def test_requires_a_field(self):
        tool = NotionTool(api_key="x")
        assert tool.update_page(page_id="p1") == {"error": "no fields to update"}

    def test_archive(self):
        tool = NotionTool(api_key="x")
        with patch(
            "requests.patch",
            return_value=_mock_response({"id": "p1", "url": "u"}),
        ) as patch_req:
            result = tool.update_page(page_id="p1", archived=True)
        assert patch_req.call_args.kwargs["json"] == {"archived": True}
        assert result == {"success": True, "id": "p1", "url": "u"}


# ── query_database_all pagination ───────────────────────────────────


class TestQueryDatabaseAll:
    def test_requires_database_id(self):
        tool = NotionTool(api_key="x")
        assert tool.query_database_all(database_id="") == [
            {"error": "database_id is required"}
        ]

    def test_paginates(self):
        tool = NotionTool(api_key="x")
        p1 = {"results": [{"id": "r1"}], "has_more": True, "next_cursor": "c2"}
        p2 = {"results": [{"id": "r2"}], "has_more": False}
        with patch(
            "requests.post", side_effect=[_mock_response(p1), _mock_response(p2)]
        ) as post:
            rows = tool.query_database_all(database_id="db")
        assert [r["id"] for r in rows] == ["r1", "r2"]
        assert post.call_args_list[1].kwargs["json"]["start_cursor"] == "c2"


# ── create_database ─────────────────────────────────────────────────


class TestCreateDatabase:
    def test_requires_parent(self):
        tool = NotionTool(api_key="x")
        assert tool.create_database(parent_page_id="", title="T") == {
            "error": "parent_page_id is required"
        }

    def test_default_schema(self):
        tool = NotionTool(api_key="x")
        with patch(
            "requests.post", return_value=_mock_response({"id": "db1", "url": "u"})
        ) as post:
            result = tool.create_database(parent_page_id="p1", title="Tasks")
        sent = post.call_args.kwargs["json"]
        assert sent["properties"] == {"Name": {"title": {}}}
        assert result == {"success": True, "id": "db1", "url": "u"}


# ── markdown ↔ blocks ───────────────────────────────────────────────


class TestMarkdownConversion:
    def test_markdown_to_blocks_types(self):
        tool = NotionTool(api_key="x")
        md = "# H1\n\n- a\n- b\n1. one\n- [x] done\n> quote\n---"
        blocks = tool.markdown_to_blocks(md)
        types = [b["type"] for b in blocks]
        assert types == [
            "heading_1",
            "bulleted_list_item",
            "bulleted_list_item",
            "numbered_list_item",
            "to_do",
            "quote",
            "divider",
        ]
        todo_block = blocks[4]
        assert todo_block["to_do"]["checked"] is True

    def test_code_fence(self):
        tool = NotionTool(api_key="x")
        blocks = tool.markdown_to_blocks("```python\nprint(1)\n```")
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "python"
        assert (
            blocks[0]["code"]["rich_text"][0]["text"]["content"] == "print(1)"
        )

    def test_roundtrip_headings_and_paragraph(self):
        tool = NotionTool(api_key="x")
        md = "# Title\nHello world"
        blocks = tool.markdown_to_blocks(md)
        # convert to a render form with plain_text for blocks_to_markdown
        rendered = [
            {
                "type": b["type"],
                b["type"]: {
                    "rich_text": [
                        {"plain_text": rt["text"]["content"]}
                        for rt in b[b["type"]]["rich_text"]
                    ]
                },
            }
            for b in blocks
        ]
        assert tool.blocks_to_markdown(rendered) == md


# ── create_page_rich ────────────────────────────────────────────────


class TestCreatePageRich:
    def test_converts_markdown_to_children(self):
        tool = NotionTool(api_key="x")
        with patch(
            "requests.post", return_value=_mock_response({"id": "pg", "url": "u"})
        ) as post:
            result = tool.create_page_rich(
                parent_id="p1", title="Doc", markdown="# Hi"
            )
        children = post.call_args.kwargs["json"]["children"]
        assert children[0]["type"] == "heading_1"
        assert result == {"success": True, "id": "pg", "url": "u"}


# ── block builder helpers ───────────────────────────────────────────


class TestBlockBuilders:
    def test_heading_clamps_level(self):
        assert heading("x", 5)["type"] == "heading_3"
        assert heading("x", 0)["type"] == "heading_1"

    def test_paragraph(self):
        assert paragraph("hi")["paragraph"]["rich_text"][0]["text"]["content"] == "hi"

    def test_lists(self):
        assert len(bulleted_list(["a", "b"])) == 2
        assert numbered_list(["a"])[0]["type"] == "numbered_list_item"

    def test_code_and_todo(self):
        assert code_block("x", "js")["code"]["language"] == "js"
        assert todo("t", checked=True)["to_do"]["checked"] is True

    def test_divider_and_callout(self):
        assert divider()["type"] == "divider"
        c = callout("note", emoji="🔥")
        assert c["callout"]["icon"]["emoji"] == "🔥"


# ── run() dispatcher wiring ──────────────────────────────────────────


class TestRunDispatcher:
    def test_routes_get_page_content(self):
        tool = NotionTool(api_key="x")
        with patch.object(tool, "get_page_content", return_value="md") as m:
            out = tool.run(action="get_page_content", page_id="p1")
        m.assert_called_once_with(page_id="p1")
        assert out == "md"

    def test_routes_query_database_all(self):
        tool = NotionTool(api_key="x")
        with patch.object(tool, "query_database_all", return_value=[]) as m:
            tool.run(action="query-database-all", database_id="db")
        m.assert_called_once_with(database_id="db")

    def test_unknown_action(self):
        tool = NotionTool(api_key="x")
        assert tool.run(action="bogus") == {"error": "Unknown action: bogus"}
