"""Notion Tool for PraisonAI Agents.

Interact with Notion workspaces - read/write page content (Blocks API),
create/update pages, query databases with cursor pagination, manage
databases and users, and convert between Markdown and Notion blocks.

Usage:
    from praisonai_tools import NotionTool

    notion = NotionTool()  # Uses NOTION_API_KEY env var

    # Search pages
    results = notion.search("meeting notes")

    # Read full page content as markdown
    text = notion.get_page_content(page_id="...")

    # Create a page from markdown
    notion.create_page_rich(parent_id="...", title="Notes", markdown="# Hi\\n- a\\n- b")

Async usage:
    from praisonai_tools.tools.notion_tool import AsyncNotionTool

    notion = AsyncNotionTool()
    text = await notion.get_page_content(page_id="...")

Environment Variables:
    NOTION_API_KEY: Notion Integration Token (Internal Integration)
"""

import os
import time
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

# Current stable Notion API version. Adds position, in_trash, meeting_notes
# properties and the DataSources API.
DEFAULT_NOTION_VERSION = "2026-03-11"

# Notion API allows ~3 requests/sec per integration.
_MAX_RETRIES = 3
_BACKOFF_BASE = 0.5


# ── Block builder helpers ───────────────────────────────────────────────


def _rich_text(text: str) -> List[Dict[str, Any]]:
    """Build a Notion rich_text array from a plain string."""
    if not text:
        return []
    return [{"type": "text", "text": {"content": text}}]


def heading(text: str, level: int = 1) -> Dict[str, Any]:
    """Build a heading block (level 1-3)."""
    level = 1 if level < 1 else 3 if level > 3 else level
    key = f"heading_{level}"
    return {"object": "block", "type": key, key: {"rich_text": _rich_text(text)}}


def paragraph(text: str) -> Dict[str, Any]:
    """Build a paragraph block."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": _rich_text(text)},
    }


def bulleted_list(items: List[str]) -> List[Dict[str, Any]]:
    """Build a list of bulleted_list_item blocks."""
    return [
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": _rich_text(item)},
        }
        for item in items
    ]


def numbered_list(items: List[str]) -> List[Dict[str, Any]]:
    """Build a list of numbered_list_item blocks."""
    return [
        {
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {"rich_text": _rich_text(item)},
        }
        for item in items
    ]


def code_block(code: str, language: str = "python") -> Dict[str, Any]:
    """Build a code block."""
    return {
        "object": "block",
        "type": "code",
        "code": {"rich_text": _rich_text(code), "language": language},
    }


def todo(text: str, checked: bool = False) -> Dict[str, Any]:
    """Build a to_do block."""
    return {
        "object": "block",
        "type": "to_do",
        "to_do": {"rich_text": _rich_text(text), "checked": checked},
    }


def divider() -> Dict[str, Any]:
    """Build a divider block."""
    return {"object": "block", "type": "divider", "divider": {}}


def callout(text: str, emoji: str = "\U0001f4a1") -> Dict[str, Any]:
    """Build a callout block."""
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": _rich_text(text),
            "icon": {"type": "emoji", "emoji": emoji},
        },
    }


def table(rows: List[List[str]]) -> Dict[str, Any]:
    """Build a table block from a 2D list of strings (first row = header)."""
    width = max((len(r) for r in rows), default=0)
    children = []
    for row in rows:
        cells = [_rich_text(str(c)) for c in row]
        while len(cells) < width:
            cells.append([])
        children.append(
            {"object": "block", "type": "table_row", "table_row": {"cells": cells}}
        )
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": width,
            "has_column_header": True,
            "has_row_header": False,
            "children": children,
        },
    }


def _extract_plain_text(rich_text: List[Dict[str, Any]]) -> str:
    """Join plain_text from a Notion rich_text array."""
    parts = []
    for rt in rich_text or []:
        parts.append(rt.get("plain_text") or rt.get("text", {}).get("content", ""))
    return "".join(parts)


# ── Markdown <-> blocks conversion ──────────────────────────────────────


def markdown_to_blocks(markdown: str) -> List[Dict[str, Any]]:
    """Convert a markdown string to a list of Notion block dicts.

    Supports headings (#, ##, ###), bullet lists (-, *), numbered lists,
    fenced code blocks (```), todos (- [ ] / - [x]), dividers (---) and
    paragraphs. Unrecognised lines become paragraphs.
    """
    blocks: List[Dict[str, Any]] = []
    lines = (markdown or "").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            language = stripped[3:].strip() or "plain text"
            code_lines: List[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append(code_block("\n".join(code_lines), language))
            i += 1
            continue

        if not stripped:
            i += 1
            continue

        if stripped in ("---", "***", "___"):
            blocks.append(divider())
        elif stripped.startswith("### "):
            blocks.append(heading(stripped[4:], 3))
        elif stripped.startswith("## "):
            blocks.append(heading(stripped[3:], 2))
        elif stripped.startswith("# "):
            blocks.append(heading(stripped[2:], 1))
        elif stripped.lower().startswith("- [x] ") or stripped.lower().startswith(
            "- [ ] "
        ):
            checked = stripped[3].lower() == "x"
            blocks.append(todo(stripped[6:], checked))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            blocks.extend(bulleted_list([stripped[2:]]))
        elif len(stripped) > 2 and stripped[0].isdigit() and stripped[1:3] == ". ":
            blocks.extend(numbered_list([stripped[3:]]))
        else:
            blocks.append(paragraph(stripped))
        i += 1
    return blocks


def blocks_to_markdown(blocks: List[Dict[str, Any]]) -> str:
    """Convert a list of Notion block dicts to a markdown string."""
    lines: List[str] = []
    for block in blocks or []:
        btype = block.get("type")
        data = block.get(btype, {}) if btype else {}
        text = _extract_plain_text(data.get("rich_text", []))

        if btype == "heading_1":
            lines.append(f"# {text}")
        elif btype == "heading_2":
            lines.append(f"## {text}")
        elif btype == "heading_3":
            lines.append(f"### {text}")
        elif btype == "bulleted_list_item":
            lines.append(f"- {text}")
        elif btype == "numbered_list_item":
            lines.append(f"1. {text}")
        elif btype == "to_do":
            mark = "x" if data.get("checked") else " "
            lines.append(f"- [{mark}] {text}")
        elif btype == "code":
            language = data.get("language", "")
            lines.append(f"```{language}\n{text}\n```")
        elif btype == "divider":
            lines.append("---")
        elif btype == "callout":
            emoji = (data.get("icon") or {}).get("emoji", "")
            lines.append(f"> {emoji} {text}".rstrip())
        elif btype == "quote":
            lines.append(f"> {text}")
        elif btype == "table":
            continue
        else:
            if text:
                lines.append(text)
    return "\n\n".join(lines)


class NotionTool(BaseTool):
    """Tool for interacting with Notion."""

    name = "notion"
    description = (
        "Interact with Notion - search, read/write page content, create and "
        "update pages, query databases, manage users."
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        validate: bool = False,
    ):
        """Initialize NotionTool.

        Args:
            api_key: Notion Integration Token (or use NOTION_API_KEY env var)
            api_version: Notion-Version header (defaults to 2026-03-11)
            validate: If True, raise ValueError when no API key is configured
        """
        self.api_key = api_key or os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
        self.api_base = "https://api.notion.com/v1"
        self.api_version = api_version or DEFAULT_NOTION_VERSION
        if validate and not self.api_key:
            raise ValueError(
                "NOTION_API_KEY is required. Set the environment variable or "
                "pass api_key=... to NotionTool()."
            )
        super().__init__()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": self.api_version,
        }

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make a Notion API request with retry/backoff on rate limits."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. Install with: pip install requests"}

        if not self.api_key:
            return {"error": "NOTION_API_KEY not configured"}

        url = f"{self.api_base}/{endpoint}"
        headers = self._headers()
        method = method.upper()

        for attempt in range(_MAX_RETRIES):
            try:
                if method == "GET":
                    response = requests.get(url, headers=headers, timeout=10)
                elif method == "POST":
                    response = requests.post(url, headers=headers, json=data or {}, timeout=10)
                elif method == "PATCH":
                    response = requests.patch(url, headers=headers, json=data or {}, timeout=10)
                elif method == "DELETE":
                    response = requests.delete(url, headers=headers, timeout=10)
                else:
                    return {"error": f"Unsupported method: {method}"}

                if response.status_code == 429 and attempt < _MAX_RETRIES - 1:
                    retry_after = float(
                        response.headers.get("Retry-After", _BACKOFF_BASE * (2 ** attempt))
                    )
                    time.sleep(retry_after)
                    continue

                result = response.json()
                if response.status_code >= 400:
                    return {"error": result.get("message", f"HTTP {response.status_code}")}
                return result
            except Exception as e:  # noqa: BLE001
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_BACKOFF_BASE * (2 ** attempt))
                    continue
                logger.error("Notion API error: %s", e)
                return {"error": str(e)}
        return {"error": "Notion API request failed after retries"}

    def _paginate(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Follow cursor pagination and return all results in one dict."""
        results: List[Dict[str, Any]] = []
        payload = dict(data or {})
        while True:
            page = self._request(method, endpoint, payload if method == "POST" else None)
            if "error" in page:
                return page
            results.extend(page.get("results", []))
            if not page.get("has_more"):
                break
            cursor = page.get("next_cursor")
            if not cursor:
                break
            if method == "POST":
                payload["start_cursor"] = cursor
            else:
                sep = "&" if "?" in endpoint else "?"
                base = endpoint.split("?")[0]
                endpoint = f"{base}{sep}start_cursor={cursor}"
        return {"results": results, "has_more": False}

    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        page_id: Optional[str] = None,
        block_id: Optional[str] = None,
        database_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        **kwargs,
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        """Execute Notion action."""
        action = action.lower().replace("-", "_")

        if action == "search":
            return self.search(query=query, **kwargs)
        elif action == "get_page":
            return self.get_page(page_id=page_id)
        elif action == "get_page_content":
            return self.get_page_content(page_id=page_id, **kwargs)
        elif action == "get_block_children":
            return self.get_block_children(block_id=block_id or page_id, **kwargs)
        elif action == "append_blocks":
            return self.append_blocks(block_id=block_id or page_id, **kwargs)
        elif action == "update_block":
            return self.update_block(block_id=block_id, **kwargs)
        elif action == "delete_block":
            return self.delete_block(block_id=block_id)
        elif action == "create_page":
            return self.create_page(parent_id=parent_id, title=title, content=content, **kwargs)
        elif action == "create_page_rich":
            return self.create_page_rich(parent_id=parent_id, title=title, **kwargs)
        elif action == "update_page":
            return self.update_page(page_id=page_id, **kwargs)
        elif action == "query_database":
            return self.query_database(database_id=database_id, **kwargs)
        elif action == "query_database_all":
            return self.query_database_all(database_id=database_id, **kwargs)
        elif action == "get_database":
            return self.get_database(database_id=database_id)
        elif action == "create_database":
            return self.create_database(parent_page_id=parent_id, title=title, **kwargs)
        elif action == "update_database":
            return self.update_database(database_id=database_id, title=title, **kwargs)
        elif action == "list_users":
            return self.list_users()
        elif action == "get_user":
            return self.get_user(user_id=kwargs.get("user_id"))
        else:
            return {"error": f"Unknown action: {action}"}

    # ── Search / Pages (existing) ───────────────────────────────────────

    def search(self, query: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search Notion workspace."""
        data = {"page_size": limit}
        if query:
            data["query"] = query

        result = self._request("POST", "search", data)

        if "error" in result:
            return [result]

        items = []
        for item in result.get("results", []):
            obj_type = item.get("object")

            if obj_type == "page":
                title = ""
                props = item.get("properties", {})
                for prop in props.values():
                    if prop.get("type") == "title":
                        title_arr = prop.get("title", [])
                        if title_arr:
                            title = title_arr[0].get("plain_text", "")
                        break

                items.append(
                    {
                        "id": item.get("id"),
                        "type": "page",
                        "title": title,
                        "url": item.get("url"),
                        "created_time": item.get("created_time"),
                    }
                )
            elif obj_type == "database":
                title = ""
                title_arr = item.get("title", [])
                if title_arr:
                    title = title_arr[0].get("plain_text", "")

                items.append(
                    {
                        "id": item.get("id"),
                        "type": "database",
                        "title": title,
                        "url": item.get("url"),
                    }
                )

        return items

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get page details (properties/metadata only)."""
        if not page_id:
            return {"error": "page_id is required"}

        result = self._request("GET", f"pages/{page_id}")

        if "error" in result:
            return result

        title = ""
        props = result.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title":
                title_arr = prop.get("title", [])
                if title_arr:
                    title = title_arr[0].get("plain_text", "")
                break

        return {
            "id": result.get("id"),
            "title": title,
            "url": result.get("url"),
            "created_time": result.get("created_time"),
            "last_edited_time": result.get("last_edited_time"),
            "properties": props,
        }

    def create_page(
        self,
        parent_id: str,
        title: str,
        content: Optional[str] = None,
        parent_type: str = "page",
    ) -> Dict[str, Any]:
        """Create a new page with an optional plain-text paragraph."""
        if not parent_id:
            return {"error": "parent_id is required"}
        if not title:
            return {"error": "title is required"}

        if parent_type == "database":
            parent = {"database_id": parent_id}
            properties = {"Name": {"title": [{"text": {"content": title}}]}}
        else:
            parent = {"page_id": parent_id}
            properties = {"title": {"title": [{"text": {"content": title}}]}}

        data = {"parent": parent, "properties": properties}

        if content:
            data["children"] = [paragraph(content)]

        result = self._request("POST", "pages", data)

        if "error" in result:
            return result

        return {"success": True, "id": result.get("id"), "url": result.get("url")}

    # ── Content (Blocks API) ────────────────────────────────────────────

    def get_block_children(
        self, block_id: str, recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieve child blocks (cursor-paginated, optionally recursive).

        Args:
            block_id: Page or block ID whose children to fetch.
            recursive: If True, inline nested children under a ``children`` key.
        """
        if not block_id:
            return [{"error": "block_id is required"}]

        result = self._paginate("GET", f"blocks/{block_id}/children")
        if "error" in result:
            return [result]

        blocks = result.get("results", [])

        if recursive:
            for block in blocks:
                if block.get("has_children"):
                    child_id = block.get("id")
                    block["children"] = self.get_block_children(child_id, recursive=True)

        return blocks

    def get_page_content(
        self, page_id: str, as_markdown: bool = True
    ) -> Union[str, List[Dict[str, Any]]]:
        """Read all blocks from a page, optionally converting to markdown."""
        if not page_id:
            return {"error": "page_id is required"} if not as_markdown else ""

        blocks = self.get_block_children(page_id, recursive=False)
        if blocks and isinstance(blocks[0], dict) and "error" in blocks[0]:
            return blocks[0].get("error", "") if as_markdown else blocks

        if as_markdown:
            return blocks_to_markdown(blocks)
        return blocks

    def append_blocks(
        self, block_id: str, blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Append child blocks to a page or block."""
        if not block_id:
            return {"error": "block_id is required"}
        if not blocks:
            return {"error": "blocks is required"}

        result = self._request(
            "PATCH", f"blocks/{block_id}/children", {"children": blocks}
        )
        if "error" in result:
            return result
        return {"success": True, "appended": len(result.get("results", []))}

    def update_block(self, block_id: str, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing block's content."""
        if not block_id:
            return {"error": "block_id is required"}
        if not block_data:
            return {"error": "block_data is required"}

        result = self._request("PATCH", f"blocks/{block_id}", block_data)
        if "error" in result:
            return result
        return {"success": True, "id": result.get("id")}

    def delete_block(self, block_id: str) -> Dict[str, Any]:
        """Archive (soft-delete) a block. Notion does not permanently delete."""
        if not block_id:
            return {"error": "block_id is required"}

        result = self._request("DELETE", f"blocks/{block_id}")
        if "error" in result:
            return result
        return {"success": True, "id": result.get("id"), "archived": True}

    # ── Pages (write) ───────────────────────────────────────────────────

    def update_page(
        self,
        page_id: str,
        properties: Optional[Dict[str, Any]] = None,
        archived: bool = False,
    ) -> Dict[str, Any]:
        """Update page properties or archive it."""
        if not page_id:
            return {"error": "page_id is required"}
        if properties is None and not archived:
            return {"error": "properties or archived is required"}

        data: Dict[str, Any] = {}
        if properties is not None:
            data["properties"] = properties
        if archived:
            data["archived"] = True

        result = self._request("PATCH", f"pages/{page_id}", data)
        if "error" in result:
            return result
        return {
            "success": True,
            "id": result.get("id"),
            "archived": result.get("archived", archived),
        }

    def create_page_rich(
        self,
        parent_id: str,
        title: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
        markdown: Optional[str] = None,
        parent_type: str = "page",
    ) -> Dict[str, Any]:
        """Create a page with rich blocks or from a markdown string."""
        if not parent_id:
            return {"error": "parent_id is required"}
        if not title:
            return {"error": "title is required"}

        if parent_type == "database":
            parent = {"database_id": parent_id}
            properties = {"Name": {"title": [{"text": {"content": title}}]}}
        else:
            parent = {"page_id": parent_id}
            properties = {"title": {"title": [{"text": {"content": title}}]}}

        children = blocks or []
        if markdown:
            children = children + markdown_to_blocks(markdown)

        data = {"parent": parent, "properties": properties}
        if children:
            data["children"] = children

        result = self._request("POST", "pages", data)
        if "error" in result:
            return result
        return {"success": True, "id": result.get("id"), "url": result.get("url")}

    # ── Databases ───────────────────────────────────────────────────────

    def query_database(
        self,
        database_id: str,
        filter_obj: Optional[Dict] = None,
        sorts: Optional[List[Dict]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query a Notion database (single page, capped at 100)."""
        if not database_id:
            return [{"error": "database_id is required"}]

        data = {"page_size": min(limit, 100)}
        if filter_obj:
            data["filter"] = filter_obj
        if sorts:
            data["sorts"] = sorts

        result = self._request("POST", f"databases/{database_id}/query", data)

        if "error" in result:
            return [result]

        return [self._extract_row(item) for item in result.get("results", [])]

    def query_database_all(
        self,
        database_id: str,
        filter_obj: Optional[Dict] = None,
        sorts: Optional[List[Dict]] = None,
    ) -> List[Dict[str, Any]]:
        """Query a database returning ALL rows via cursor pagination."""
        if not database_id:
            return [{"error": "database_id is required"}]

        data: Dict[str, Any] = {"page_size": 100}
        if filter_obj:
            data["filter"] = filter_obj
        if sorts:
            data["sorts"] = sorts

        result = self._paginate("POST", f"databases/{database_id}/query", data)
        if "error" in result:
            return [result]

        return [self._extract_row(item) for item in result.get("results", [])]

    @staticmethod
    def _extract_row(item: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten a database row's properties into simple values."""
        props = item.get("properties", {})
        extracted: Dict[str, Any] = {"id": item.get("id"), "url": item.get("url")}
        for name, prop in props.items():
            prop_type = prop.get("type")
            if prop_type == "title":
                arr = prop.get("title", [])
                extracted[name] = arr[0].get("plain_text", "") if arr else ""
            elif prop_type == "rich_text":
                arr = prop.get("rich_text", [])
                extracted[name] = arr[0].get("plain_text", "") if arr else ""
            elif prop_type == "number":
                extracted[name] = prop.get("number")
            elif prop_type == "select":
                sel = prop.get("select")
                extracted[name] = sel.get("name") if sel else None
            elif prop_type == "multi_select":
                extracted[name] = [s.get("name") for s in prop.get("multi_select", [])]
            elif prop_type == "checkbox":
                extracted[name] = prop.get("checkbox")
            elif prop_type == "date":
                date = prop.get("date")
                extracted[name] = date.get("start") if date else None
            elif prop_type == "people":
                extracted[name] = [p.get("name") for p in prop.get("people", [])]
            elif prop_type == "url":
                extracted[name] = prop.get("url")
            elif prop_type == "email":
                extracted[name] = prop.get("email")
            elif prop_type == "phone_number":
                extracted[name] = prop.get("phone_number")
            elif prop_type == "status":
                status = prop.get("status")
                extracted[name] = status.get("name") if status else None
        return extracted

    def get_database(self, database_id: str) -> Dict[str, Any]:
        """Get database schema/info."""
        if not database_id:
            return {"error": "database_id is required"}

        result = self._request("GET", f"databases/{database_id}")

        if "error" in result:
            return result

        title = ""
        title_arr = result.get("title", [])
        if title_arr:
            title = title_arr[0].get("plain_text", "")

        props = {}
        for name, prop in result.get("properties", {}).items():
            props[name] = {"type": prop.get("type")}

        return {
            "id": result.get("id"),
            "title": title,
            "url": result.get("url"),
            "properties": props,
        }

    def create_database(
        self, parent_page_id: str, title: str, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new inline database inside a page.

        Args:
            parent_page_id: Page to create the database under.
            title: Database title.
            properties: Property schema, e.g. {"Name": {"title": {}}}.
        """
        if not parent_page_id:
            return {"error": "parent_page_id is required"}
        if not title:
            return {"error": "title is required"}
        if not properties:
            return {"error": "properties is required"}

        data = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties,
        }

        result = self._request("POST", "databases", data)
        if "error" in result:
            return result
        return {"success": True, "id": result.get("id"), "url": result.get("url")}

    def update_database(
        self,
        database_id: str,
        title: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update a database's title or property schema."""
        if not database_id:
            return {"error": "database_id is required"}
        if title is None and properties is None:
            return {"error": "title or properties is required"}

        data: Dict[str, Any] = {}
        if title is not None:
            data["title"] = [{"type": "text", "text": {"content": title}}]
        if properties is not None:
            data["properties"] = properties

        result = self._request("PATCH", f"databases/{database_id}", data)
        if "error" in result:
            return result
        return {"success": True, "id": result.get("id")}

    # ── Users ───────────────────────────────────────────────────────────

    def list_users(self) -> List[Dict[str, Any]]:
        """List workspace members (cursor-paginated)."""
        result = self._paginate("GET", "users")
        if "error" in result:
            return [result]
        return [
            {
                "id": u.get("id"),
                "name": u.get("name"),
                "type": u.get("type"),
                "email": (u.get("person") or {}).get("email"),
            }
            for u in result.get("results", [])
        ]

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get a specific user by ID."""
        if not user_id:
            return {"error": "user_id is required"}
        result = self._request("GET", f"users/{user_id}")
        if "error" in result:
            return result
        return {
            "id": result.get("id"),
            "name": result.get("name"),
            "type": result.get("type"),
            "email": (result.get("person") or {}).get("email"),
        }

    # ── Markdown converters (instance methods) ──────────────────────────

    def markdown_to_blocks(self, markdown: str) -> List[Dict[str, Any]]:
        """Convert a markdown string to a Notion block list."""
        return markdown_to_blocks(markdown)

    def blocks_to_markdown(self, blocks: List[Dict[str, Any]]) -> str:
        """Convert Notion blocks to a markdown string."""
        return blocks_to_markdown(blocks)


class AsyncNotionTool(NotionTool):
    """Async variant of NotionTool using httpx.

    Falls back gracefully with a clear error if httpx is not installed.
    """

    async def _request(  # type: ignore[override]
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Dict:
        try:
            import httpx
        except ImportError:
            return {"error": "httpx not installed. Install with: pip install httpx"}

        if not self.api_key:
            return {"error": "NOTION_API_KEY not configured"}

        import asyncio

        url = f"{self.api_base}/{endpoint}"
        headers = self._headers()
        method = method.upper()

        async with httpx.AsyncClient(timeout=10) as client:
            for attempt in range(_MAX_RETRIES):
                try:
                    if method == "GET":
                        response = await client.get(url, headers=headers)
                    elif method == "POST":
                        response = await client.post(url, headers=headers, json=data or {})
                    elif method == "PATCH":
                        response = await client.patch(url, headers=headers, json=data or {})
                    elif method == "DELETE":
                        response = await client.delete(url, headers=headers)
                    else:
                        return {"error": f"Unsupported method: {method}"}

                    if response.status_code == 429 and attempt < _MAX_RETRIES - 1:
                        retry_after = float(
                            response.headers.get(
                                "Retry-After", _BACKOFF_BASE * (2 ** attempt)
                            )
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    result = response.json()
                    if response.status_code >= 400:
                        return {
                            "error": result.get("message", f"HTTP {response.status_code}")
                        }
                    return result
                except Exception as e:  # noqa: BLE001
                    if attempt < _MAX_RETRIES - 1:
                        await asyncio.sleep(_BACKOFF_BASE * (2 ** attempt))
                        continue
                    logger.error("Notion async API error: %s", e)
                    return {"error": str(e)}
        return {"error": "Notion API request failed after retries"}

    async def _paginate(  # type: ignore[override]
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Dict:
        results: List[Dict[str, Any]] = []
        payload = dict(data or {})
        while True:
            page = await self._request(method, endpoint, payload if method == "POST" else None)
            if "error" in page:
                return page
            results.extend(page.get("results", []))
            if not page.get("has_more"):
                break
            cursor = page.get("next_cursor")
            if not cursor:
                break
            if method == "POST":
                payload["start_cursor"] = cursor
            else:
                sep = "&" if "?" in endpoint else "?"
                base = endpoint.split("?")[0]
                endpoint = f"{base}{sep}start_cursor={cursor}"
        return {"results": results, "has_more": False}

    async def get_block_children(  # type: ignore[override]
        self, block_id: str, recursive: bool = False
    ) -> List[Dict[str, Any]]:
        if not block_id:
            return [{"error": "block_id is required"}]
        result = await self._paginate("GET", f"blocks/{block_id}/children")
        if "error" in result:
            return [result]
        blocks = result.get("results", [])
        if recursive:
            for block in blocks:
                if block.get("has_children"):
                    block["children"] = await self.get_block_children(
                        block.get("id"), recursive=True
                    )
        return blocks

    async def get_page_content(  # type: ignore[override]
        self, page_id: str, as_markdown: bool = True
    ) -> Union[str, List[Dict[str, Any]]]:
        if not page_id:
            return "" if as_markdown else {"error": "page_id is required"}
        blocks = await self.get_block_children(page_id, recursive=False)
        if blocks and isinstance(blocks[0], dict) and "error" in blocks[0]:
            return blocks[0].get("error", "") if as_markdown else blocks
        return blocks_to_markdown(blocks) if as_markdown else blocks

    async def append_blocks(  # type: ignore[override]
        self, block_id: str, blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not block_id:
            return {"error": "block_id is required"}
        if not blocks:
            return {"error": "blocks is required"}
        result = await self._request(
            "PATCH", f"blocks/{block_id}/children", {"children": blocks}
        )
        if "error" in result:
            return result
        return {"success": True, "appended": len(result.get("results", []))}

    async def query_database_all(  # type: ignore[override]
        self,
        database_id: str,
        filter_obj: Optional[Dict] = None,
        sorts: Optional[List[Dict]] = None,
    ) -> List[Dict[str, Any]]:
        if not database_id:
            return [{"error": "database_id is required"}]
        data: Dict[str, Any] = {"page_size": 100}
        if filter_obj:
            data["filter"] = filter_obj
        if sorts:
            data["sorts"] = sorts
        result = await self._paginate("POST", f"databases/{database_id}/query", data)
        if "error" in result:
            return [result]
        return [self._extract_row(item) for item in result.get("results", [])]


def search_notion(query: str) -> List[Dict[str, Any]]:
    """Search Notion workspace."""
    return NotionTool().search(query=query)


def create_notion_page(parent_id: str, title: str, content: Optional[str] = None) -> Dict[str, Any]:
    """Create a Notion page."""
    return NotionTool().create_page(parent_id=parent_id, title=title, content=content)
