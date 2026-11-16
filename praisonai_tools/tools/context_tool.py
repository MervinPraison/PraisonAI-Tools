"""Context.dev search and Markdown scraping; install praisonai-tools[context]."""

import os
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

from praisonai_tools.tools.base import BaseTool


class ContextTool(BaseTool):
    """Search the web or scrape a URL using CONTEXT_DEV_API_KEY."""

    name = "context"
    description = "Search the live web or scrape a URL into Markdown with Context.dev."
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["search", "scrape"],
                "default": "search",
                "description": "Search the web or scrape one page.",
            },
            "query": {
                "type": "string",
                "description": "Search query; required for search.",
            },
            "url": {
                "type": "string",
                "description": "HTTP(S) URL; required for scrape.",
            },
            "num_results": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 10,
                "description": "Maximum search results to return.",
            },
        },
        "additionalProperties": False,
    }

    def __init__(self, api_key: Optional[str] = None):
        """Use an explicit key or CONTEXT_DEV_API_KEY."""
        self.api_key = api_key or os.getenv("CONTEXT_DEV_API_KEY")
        super().__init__()

    def run(
        self,
        action: str = "search",
        query: str = "",
        url: str = "",
        num_results: int = 10,
    ) -> Dict[str, Any]:
        """Run search with query or scrape with url; return the API's JSON result."""
        if action not in ("search", "scrape"):
            return {"error": "action must be search or scrape"}
        if not self.api_key:
            return {"error": "CONTEXT_DEV_API_KEY is required"}
        if action == "search":
            if not isinstance(query, str) or not query.strip():
                return {"error": "query is required for search"}
            if type(num_results) is not int or not 1 <= num_results <= 100:
                return {"error": "num_results must be an integer from 1 to 100"}
            payload = {"query": query, "numResults": num_results}
        else:
            try:
                target = urlsplit(url)
                if target.scheme not in ("http", "https") or not target.hostname:
                    return {"error": "url must be an HTTP(S) URL"}
            except (TypeError, ValueError, AttributeError):
                return {"error": "url must be an HTTP(S) URL"}
            payload = {"url": url, "formats": {"markdown": True}}
        try:
            import httpx
        except ImportError:
            return {
                "error": "Install Context.dev support: pip install 'praisonai-tools[context]'"
            }
        try:
            response = httpx.post(
                f"https://api.context.dev/v1/web/{action}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=180.0,
                follow_redirects=False,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return {"error": "Context.dev request failed"}
        except ValueError:
            return {"error": "Context.dev returned invalid JSON"}
