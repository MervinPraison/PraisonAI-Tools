"""Web search and page extraction through WebRouter (pip install webrouter>=0.16)."""

import logging
from typing import Any, Dict, Optional

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class WebRouterTool(BaseTool):
    """Search and extract with automatic backend fallback, including keyless backends."""

    name = "webrouter"
    description = "Search the web or extract the contents of a web page using WebRouter."

    def __init__(self, provider: str = "auto", extract_provider: str = "auto"):
        self.provider = provider
        self.extract_provider = extract_provider
        super().__init__()

    def run(self, action: str = "search", query: Optional[str] = None,
            url: Optional[str] = None, max_results: int = 5) -> Dict[str, Any]:
        if action == "search":
            return self.search(query=query, max_results=max_results)
        if action == "extract":
            return self.extract(url=url)
        return {"error": f"Unknown action: {action}"}

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web; return a query and results with title, url and content."""
        if not query:
            return {"error": "query is required"}
        try:
            from web_router import WebRouter
        except ImportError:
            return {"error": "webrouter not installed. Install with: pip install 'webrouter>=0.16'"}
        try:
            with WebRouter() as router:
                response = router.search(query, provider=self.provider, max_results=max_results)
            return {"query": query, "results": [
                {"title": r.title, "url": r.url, "content": r.content}
                for r in response.results
            ]}
        except Exception as exc:
            logger.error("WebRouter search error: %s", exc)
            return {"error": str(exc)}

    def extract(self, url: str) -> Dict[str, Any]:
        """Extract a web page; return documents with url and content."""
        if not url:
            return {"error": "url is required"}
        try:
            from web_router import WebRouter
        except ImportError:
            return {"error": "webrouter not installed. Install with: pip install 'webrouter>=0.16'"}
        try:
            with WebRouter() as router:
                response = router.extract(url, provider=self.extract_provider)
            return {"documents": [
                {"url": d.url, "content": d.content} for d in response.documents
            ]}
        except Exception as exc:
            logger.error("WebRouter extract error: %s", exc)
            return {"error": str(exc)}


def webrouter_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Search the web using WebRouter's automatic backend selection."""
    return WebRouterTool().search(query=query, max_results=max_results)


def webrouter_extract(url: str) -> Dict[str, Any]:
    """Extract a web page using WebRouter's automatic backend selection."""
    return WebRouterTool().extract(url=url)
