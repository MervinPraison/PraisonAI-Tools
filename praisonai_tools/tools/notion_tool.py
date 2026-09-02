"""Notion Tool for PraisonAI Agents.

Interact with Notion workspaces - create pages, query databases, update content.

Usage:
    from praisonai_tools import NotionTool
    
    notion = NotionTool()  # Uses NOTION_API_KEY env var
    
    # Search pages
    results = notion.search("meeting notes")
    
    # Create a page
    notion.create_page(parent_id="...", title="New Page", content="Hello!")

    # Read a page's content as markdown
    markdown = notion.get_page_content(page_id="...")

    # Create a rich page from markdown
    notion.create_page_rich(parent_id="...", title="Doc", markdown="# Hi\n- a\n- b")

    # Append structured blocks
    from praisonai_tools.tools.notion_tool import heading, paragraph, todo
    notion.append_blocks(block_id="...", blocks=[heading("Tasks"), todo("Ship it")])

    # Query all rows (cursor pagination, not capped at 100)
    rows = notion.query_database_all(database_id="...")

Environment Variables:
    NOTION_API_KEY: Notion Integration Token (Internal Integration)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class NotionTool(BaseTool):
    """Tool for interacting with Notion."""
    
    name = "notion"
    description = "Interact with Notion - search, create pages, query databases."
    
    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        """Initialize NotionTool.
        
        Args:
            api_key: Notion Integration Token (or use NOTION_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
        self.api_base = "https://api.notion.com/v1"
        self.api_version = "2026-03-11"
        super().__init__()

    def _request_full(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Dict:
        """Make a Notion API request supporting GET query params.

        Unlike :meth:`_request`, GET requests pass ``data`` as query params so
        endpoints like ``blocks/{id}/children?start_cursor=...`` work.
        """
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        if not self.api_key:
            return {"error": "NOTION_API_KEY not configured"}

        try:
            url = f"{self.api_base}/{endpoint}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Notion-Version": self.api_version,
            }

            if method == "GET":
                response = requests.get(
                    url, headers=headers, params=data or None, timeout=10
                )
            elif method == "POST":
                response = requests.post(
                    url, headers=headers, json=data or {}, timeout=10
                )
            elif method == "PATCH":
                response = requests.patch(
                    url, headers=headers, json=data or {}, timeout=10
                )
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return {"error": f"Unsupported method: {method}"}

            result = response.json()

            if response.status_code >= 400:
                return {"error": result.get("message", f"HTTP {response.status_code}")}

            return result
        except Exception as e:
            logger.error(f"Notion API error: {e}")
            return {"error": str(e)}
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make Notion API request."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        if not self.api_key:
            return {"error": "NOTION_API_KEY not configured"}
        
        try:
            url = f"{self.api_base}/{endpoint}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Notion-Version": self.api_version,
            }
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data or {}, timeout=10)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data or {}, timeout=10)
            else:
                return {"error": f"Unsupported method: {method}"}
            
            result = response.json()
            
            if response.status_code >= 400:
                return {"error": result.get("message", f"HTTP {response.status_code}")}
            
            return result
        except Exception as e:
            logger.error(f"Notion API error: {e}")
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        page_id: Optional[str] = None,
        database_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        """Execute Notion action."""
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(query=query)
        elif action == "get_page":
            return self.get_page(page_id=page_id)
        elif action == "create_page":
            return self.create_page(parent_id=parent_id, title=title, content=content)
        elif action == "query_database":
            return self.query_database(database_id=database_id, **kwargs)
        elif action == "get_database":
            return self.get_database(database_id=database_id)
        elif action == "get_page_content":
            return self.get_page_content(page_id=page_id, **kwargs)
        elif action == "get_block_children":
            block_id = kwargs.pop("block_id", None) or page_id
            return self.get_block_children(block_id=block_id, **kwargs)
        elif action == "append_blocks":
            block_id = kwargs.pop("block_id", None) or page_id
            return self.append_blocks(block_id=block_id, **kwargs)
        elif action == "delete_block":
            block_id = kwargs.pop("block_id", None)
            return self.delete_block(block_id=block_id)
        elif action == "update_page":
            return self.update_page(page_id=page_id, **kwargs)
        elif action == "query_database_all":
            return self.query_database_all(database_id=database_id, **kwargs)
        elif action == "create_database":
            return self.create_database(parent_page_id=parent_id, title=title, **kwargs)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(self, query: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search Notion workspace.
        
        Args:
            query: Search query
            limit: Max results
            
        Returns:
            List of search results
        """
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
                
                items.append({
                    "id": item.get("id"),
                    "type": "page",
                    "title": title,
                    "url": item.get("url"),
                    "created_time": item.get("created_time"),
                })
            elif obj_type == "database":
                title = ""
                title_arr = item.get("title", [])
                if title_arr:
                    title = title_arr[0].get("plain_text", "")
                
                items.append({
                    "id": item.get("id"),
                    "type": "database",
                    "title": title,
                    "url": item.get("url"),
                })
        
        return items
    
    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get page details.
        
        Args:
            page_id: Notion page ID
            
        Returns:
            Page details
        """
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
        """Create a new page.
        
        Args:
            parent_id: Parent page or database ID
            title: Page title
            content: Page content (plain text)
            parent_type: "page" or "database"
            
        Returns:
            Created page info
        """
        if not parent_id:
            return {"error": "parent_id is required"}
        if not title:
            return {"error": "title is required"}
        
        # Build parent reference
        if parent_type == "database":
            parent = {"database_id": parent_id}
            properties = {
                "Name": {"title": [{"text": {"content": title}}]}
            }
        else:
            parent = {"page_id": parent_id}
            properties = {
                "title": {"title": [{"text": {"content": title}}]}
            }
        
        data = {
            "parent": parent,
            "properties": properties,
        }
        
        # Add content as children blocks
        if content:
            data["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    }
                }
            ]
        
        result = self._request("POST", "pages", data)
        
        if "error" in result:
            return result
        
        return {
            "success": True,
            "id": result.get("id"),
            "url": result.get("url"),
        }
    
    def query_database(
        self,
        database_id: str,
        filter_obj: Optional[Dict] = None,
        sorts: Optional[List[Dict]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query a Notion database.
        
        Args:
            database_id: Database ID
            filter_obj: Notion filter object
            sorts: Sort configuration
            limit: Max results
            
        Returns:
            List of database entries
        """
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
        
        items = []
        for item in result.get("results", []):
            props = item.get("properties", {})
            
            # Extract property values
            extracted = {"id": item.get("id"), "url": item.get("url")}
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
            
            items.append(extracted)
        
        return items
    
    def get_database(self, database_id: str) -> Dict[str, Any]:
        """Get database schema/info.
        
        Args:
            database_id: Database ID
            
        Returns:
            Database info
        """
        if not database_id:
            return {"error": "database_id is required"}
        
        result = self._request("GET", f"databases/{database_id}")
        
        if "error" in result:
            return result
        
        title = ""
        title_arr = result.get("title", [])
        if title_arr:
            title = title_arr[0].get("plain_text", "")
        
        # Extract property schema
        props = {}
        for name, prop in result.get("properties", {}).items():
            props[name] = {"type": prop.get("type")}
        
        return {
            "id": result.get("id"),
            "title": title,
            "url": result.get("url"),
            "properties": props,
        }

    # ── Blocks API (content) ──────────────────────────────────────────

    def get_block_children(
        self, block_id: str, recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieve child blocks of a page or block (cursor-paginated).

        Args:
            block_id: Page ID or block ID whose children to fetch.
            recursive: If True, fetch nested children for blocks that have them.

        Returns:
            Flat list of block objects (nested children attached under
            ``_children`` when ``recursive=True``).
        """
        if not block_id:
            return [{"error": "block_id is required"}]

        blocks: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        while True:
            params: Dict[str, Any] = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            result = self._request_full(
                "GET", f"blocks/{block_id}/children", params
            )
            if "error" in result:
                return [result]
            blocks.extend(result.get("results", []))
            if not result.get("has_more"):
                break
            cursor = result.get("next_cursor")

        if recursive:
            for block in blocks:
                if block.get("has_children"):
                    child_id = block.get("id")
                    if child_id:
                        block["_children"] = self.get_block_children(
                            child_id, recursive=True
                        )

        return blocks

    def get_page_content(
        self, page_id: str, as_markdown: bool = True
    ) -> Union[str, List[Dict[str, Any]]]:
        """Read all blocks from a page, optionally converting to markdown.

        Args:
            page_id: Notion page ID.
            as_markdown: If True return a markdown string, else raw blocks.

        Returns:
            Markdown string or list of block objects.
        """
        if not page_id:
            return {"error": "page_id is required"} if not as_markdown else ""

        blocks = self.get_block_children(page_id, recursive=True)
        if blocks and isinstance(blocks[0], dict) and "error" in blocks[0]:
            return blocks[0]["error"] if as_markdown else blocks

        if as_markdown:
            return self.blocks_to_markdown(blocks)
        return blocks

    def append_blocks(
        self, block_id: str, blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Append block children to a page or block.

        Args:
            block_id: Target page or block ID.
            blocks: List of Notion block objects to append.

        Returns:
            API response or error dict.
        """
        if not block_id:
            return {"error": "block_id is required"}
        if not blocks:
            return {"error": "blocks is required"}

        result = self._request_full(
            "PATCH", f"blocks/{block_id}/children", {"children": blocks}
        )
        if "error" in result:
            return result
        return {"success": True, "results": result.get("results", [])}

    def update_block(
        self, block_id: str, block_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing block's content.

        Args:
            block_id: Block ID to update.
            block_data: Partial block payload (e.g. ``{"paragraph": {...}}``).
        """
        if not block_id:
            return {"error": "block_id is required"}
        if not block_data:
            return {"error": "block_data is required"}

        result = self._request_full("PATCH", f"blocks/{block_id}", block_data)
        if "error" in result:
            return result
        return {"success": True, "id": result.get("id")}

    def delete_block(self, block_id: str) -> Dict[str, Any]:
        """Archive (soft-delete) a block. Notion never hard-deletes via API."""
        if not block_id:
            return {"error": "block_id is required"}

        result = self._request_full("DELETE", f"blocks/{block_id}")
        if "error" in result:
            return result
        return {"success": True, "id": result.get("id")}

    # ── Pages ─────────────────────────────────────────────────────────

    def update_page(
        self,
        page_id: str,
        properties: Optional[Dict[str, Any]] = None,
        archived: bool = False,
    ) -> Dict[str, Any]:
        """Update page properties and/or archive it.

        Args:
            page_id: Page ID to update.
            properties: Notion properties payload.
            archived: When True, archive (trash) the page.
        """
        if not page_id:
            return {"error": "page_id is required"}
        if not properties and not archived:
            return {"error": "no fields to update"}

        data: Dict[str, Any] = {}
        if properties:
            data["properties"] = properties
        if archived:
            data["archived"] = True

        result = self._request_full("PATCH", f"pages/{page_id}", data)
        if "error" in result:
            return result
        return {"success": True, "id": result.get("id"), "url": result.get("url")}

    # ── Databases ─────────────────────────────────────────────────────

    def query_database_all(
        self,
        database_id: str,
        filter_obj: Optional[Dict] = None,
        sorts: Optional[List[Dict]] = None,
    ) -> List[Dict[str, Any]]:
        """Query a database returning ALL rows via cursor pagination.

        Unlike :meth:`query_database`, this is not capped at 100 rows.
        """
        if not database_id:
            return [{"error": "database_id is required"}]

        rows: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        while True:
            data: Dict[str, Any] = {"page_size": 100}
            if filter_obj:
                data["filter"] = filter_obj
            if sorts:
                data["sorts"] = sorts
            if cursor:
                data["start_cursor"] = cursor

            result = self._request_full(
                "POST", f"databases/{database_id}/query", data
            )
            if "error" in result:
                return [result]
            rows.extend(result.get("results", []))
            if not result.get("has_more"):
                break
            cursor = result.get("next_cursor")

        return rows

    def create_database(
        self,
        parent_page_id: str,
        title: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new inline database inside a page.

        Args:
            parent_page_id: Parent page ID that will contain the database.
            title: Database title.
            properties: Property schema. Defaults to a single ``Name`` title
                column when omitted.
        """
        if not parent_page_id:
            return {"error": "parent_page_id is required"}
        if not title:
            return {"error": "title is required"}

        data = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties or {"Name": {"title": {}}},
        }
        result = self._request_full("POST", "databases", data)
        if "error" in result:
            return result
        return {"success": True, "id": result.get("id"), "url": result.get("url")}

    # ── Markdown ↔ Blocks converter ───────────────────────────────────

    @staticmethod
    def _rich_text(block: Dict[str, Any]) -> str:
        """Join plain_text from a block's rich_text array."""
        btype = block.get("type", "")
        payload = block.get(btype, {})
        parts = payload.get("rich_text", []) if isinstance(payload, dict) else []
        return "".join(p.get("plain_text", "") for p in parts)

    def blocks_to_markdown(self, blocks: List[Dict[str, Any]]) -> str:
        """Convert Notion blocks to a markdown string (best-effort)."""
        lines: List[str] = []
        for block in blocks or []:
            btype = block.get("type", "")
            text = self._rich_text(block)
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
                checked = block.get("to_do", {}).get("checked", False)
                lines.append(f"- [{'x' if checked else ' '}] {text}")
            elif btype == "code":
                lang = block.get("code", {}).get("language", "")
                lines.append(f"```{lang}\n{text}\n```")
            elif btype == "quote":
                lines.append(f"> {text}")
            elif btype == "divider":
                lines.append("---")
            elif btype == "callout":
                emoji = (block.get("callout", {}).get("icon") or {}).get("emoji", "")
                lines.append(f"> {emoji} {text}".rstrip())
            else:
                if text:
                    lines.append(text)
        return "\n".join(lines)

    def markdown_to_blocks(self, markdown: str) -> List[Dict[str, Any]]:
        """Convert a markdown string to a list of Notion blocks (best-effort)."""

        def _text(content: str) -> Dict[str, Any]:
            return {"rich_text": [{"type": "text", "text": {"content": content}}]}

        blocks: List[Dict[str, Any]] = []
        lines = (markdown or "").split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if stripped.startswith("```"):
                lang = stripped[3:].strip() or "plain text"
                code_lines: List[str] = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "\n".join(code_lines)}}
                        ],
                        "language": lang,
                    },
                })
                i += 1
                continue

            if not stripped:
                i += 1
                continue

            if stripped.startswith("### "):
                blocks.append({"object": "block", "type": "heading_3", "heading_3": _text(stripped[4:])})
            elif stripped.startswith("## "):
                blocks.append({"object": "block", "type": "heading_2", "heading_2": _text(stripped[3:])})
            elif stripped.startswith("# "):
                blocks.append({"object": "block", "type": "heading_1", "heading_1": _text(stripped[2:])})
            elif stripped in ("---", "***", "___"):
                blocks.append({"object": "block", "type": "divider", "divider": {}})
            elif stripped.startswith("> "):
                blocks.append({"object": "block", "type": "quote", "quote": _text(stripped[2:])})
            elif stripped.startswith("- [ ] ") or stripped.startswith("- [x] "):
                checked = stripped[3] == "x"
                todo = _text(stripped[6:])
                todo["checked"] = checked
                blocks.append({"object": "block", "type": "to_do", "to_do": todo})
            elif stripped.startswith(("- ", "* ")):
                blocks.append({"object": "block", "type": "bulleted_list_item", "bulleted_list_item": _text(stripped[2:])})
            elif len(stripped) > 2 and stripped[0].isdigit() and stripped[1:3] == ". ":
                blocks.append({"object": "block", "type": "numbered_list_item", "numbered_list_item": _text(stripped[3:])})
            else:
                blocks.append({"object": "block", "type": "paragraph", "paragraph": _text(stripped)})
            i += 1

        return blocks

    def create_page_rich(
        self,
        parent_id: str,
        title: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
        markdown: Optional[str] = None,
        parent_type: str = "page",
    ) -> Dict[str, Any]:
        """Create a page with rich blocks or from a markdown string.

        Args:
            parent_id: Parent page or database ID.
            title: Page title.
            blocks: Explicit Notion blocks (takes precedence over markdown).
            markdown: Markdown converted to blocks when ``blocks`` is None.
            parent_type: "page" or "database".
        """
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

        children = blocks
        if children is None and markdown:
            children = self.markdown_to_blocks(markdown)

        data: Dict[str, Any] = {"parent": parent, "properties": properties}
        if children:
            data["children"] = children

        result = self._request_full("POST", "pages", data)
        if "error" in result:
            return result
        return {"success": True, "id": result.get("id"), "url": result.get("url")}


def search_notion(query: str) -> List[Dict[str, Any]]:
    """Search Notion workspace."""
    return NotionTool().search(query=query)


def create_notion_page(parent_id: str, title: str, content: Optional[str] = None) -> Dict[str, Any]:
    """Create a Notion page."""
    return NotionTool().create_page(parent_id=parent_id, title=title, content=content)


# ── Block builder helpers ─────────────────────────────────────────────


def _rich(content: str) -> Dict[str, Any]:
    return {"rich_text": [{"type": "text", "text": {"content": content}}]}


def heading(text: str, level: int = 1) -> Dict[str, Any]:
    """Build a heading block (level 1-3)."""
    level = max(1, min(3, level))
    key = f"heading_{level}"
    return {"object": "block", "type": key, key: _rich(text)}


def paragraph(text: str) -> Dict[str, Any]:
    """Build a paragraph block."""
    return {"object": "block", "type": "paragraph", "paragraph": _rich(text)}


def bulleted_list(items: List[str]) -> List[Dict[str, Any]]:
    """Build a list of bulleted list-item blocks."""
    return [
        {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": _rich(i)}
        for i in items
    ]


def numbered_list(items: List[str]) -> List[Dict[str, Any]]:
    """Build a list of numbered list-item blocks."""
    return [
        {"object": "block", "type": "numbered_list_item", "numbered_list_item": _rich(i)}
        for i in items
    ]


def code_block(code: str, language: str = "python") -> Dict[str, Any]:
    """Build a code block."""
    block = {"object": "block", "type": "code", "code": _rich(code)}
    block["code"]["language"] = language
    return block


def todo(text: str, checked: bool = False) -> Dict[str, Any]:
    """Build a to-do block."""
    payload = _rich(text)
    payload["checked"] = checked
    return {"object": "block", "type": "to_do", "to_do": payload}


def divider() -> Dict[str, Any]:
    """Build a divider block."""
    return {"object": "block", "type": "divider", "divider": {}}


def callout(text: str, emoji: str = "\U0001f4a1") -> Dict[str, Any]:
    """Build a callout block."""
    payload = _rich(text)
    payload["icon"] = {"type": "emoji", "emoji": emoji}
    return {"object": "block", "type": "callout", "callout": payload}
