"""Unit tests for NotionTool.get_page_content."""

from unittest.mock import MagicMock, patch

from praisonai_tools.tools.notion_tool import NotionTool


def _resp(payload, status_code=200):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.status_code = status_code
    return resp


def _block(btype, text="", **extra):
    return {"type": btype, btype: {"rich_text": [{"plain_text": text}], **extra}}


def test_requires_page_id():
    assert NotionTool(api_key="x").get_page_content("") == {"error": "page_id is required"}


def test_converts_blocks_to_markdown():
    payload = {
        "results": [
            _block("heading_1", "Title"),
            _block("paragraph", "body"),
            _block("bulleted_list_item", "a"),
            _block("numbered_list_item", "b"),
            _block("to_do", "done", checked=True),
            _block("code", "print(1)", language="python"),
            {"type": "divider", "divider": {}},
        ],
        "has_more": False,
    }
    with patch("requests.get", return_value=_resp(payload)) as get:
        md = NotionTool(api_key="x").get_page_content("page1")
    assert md == "# Title\n\nbody\n\n- a\n\n1. b\n\n- [x] done\n\n```python\nprint(1)\n```\n\n---"
    assert get.call_args[0][0].endswith("/blocks/page1/children?page_size=100")


def test_follows_pagination():
    pages = [
        _resp({"results": [_block("paragraph", "one")], "has_more": True, "next_cursor": "c2"}),
        _resp({"results": [_block("paragraph", "two")], "has_more": False}),
    ]
    with patch("requests.get", side_effect=pages) as get:
        md = NotionTool(api_key="x").get_page_content("page1")
    assert md == "one\n\ntwo"
    assert get.call_args_list[1][0][0].endswith("start_cursor=c2")


def test_returns_api_error():
    with patch("requests.get", return_value=_resp({"message": "Not found"}, 404)):
        assert NotionTool(api_key="x").get_page_content("p") == {"error": "Not found"}


def test_run_dispatches_get_page_content():
    tool = NotionTool(api_key="x")
    with patch.object(tool, "get_page_content", return_value="md") as m:
        assert tool.run(action="get_page_content", page_id="p") == "md"
    m.assert_called_once_with(page_id="p")
