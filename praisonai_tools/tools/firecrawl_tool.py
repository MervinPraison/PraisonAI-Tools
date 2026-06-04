"""Firecrawl Tool for PraisonAI Agents.

Web scraping and crawling using Firecrawl API.

Usage:
    from praisonai_tools import FirecrawlTool
    
    fc = FirecrawlTool()
    content = fc.scrape("https://example.com")

Environment Variables:
    FIRECRAWL_API_KEY: Firecrawl API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class FirecrawlTool(BaseTool):
    """Tool for web scraping using Firecrawl."""
    
    name = "firecrawl"
    description = "Scrape and crawl websites using Firecrawl."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("FIRECRAWL_API_KEY is required")
            try:
                from firecrawl import Firecrawl
            except ImportError:
                raise ImportError(
                    "firecrawl-py>=4 not installed. Install with: pip install 'firecrawl-py>=4'"
                )
            self._client = Firecrawl(api_key=self.api_key)
        return self._client
    
    def run(
        self,
        action: str = "scrape",
        url: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "scrape":
            return self.scrape(url=url, **kwargs)
        elif action == "crawl":
            return self.crawl(url=url, **kwargs)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def scrape(self, url: str, formats: List[str] = None) -> Dict[str, Any]:
        """Scrape a single URL."""
        if not url:
            return {"error": "url is required"}
        
        if not self.api_key:
            return {"error": "FIRECRAWL_API_KEY not configured"}
        
        try:
            # firecrawl-py v2 (>=4): kwargs instead of a params dict; returns a
            # typed Document, not a dict.
            kwargs: Dict[str, Any] = {}
            if formats:
                kwargs["formats"] = formats

            result = self.client.scrape(url, **kwargs)

            # v2 returns a Document object; metadata is a typed DocumentMetadata.
            # Coerce to a plain dict to keep this tool's return shape stable.
            metadata = getattr(result, "metadata", None)
            if metadata is not None and hasattr(metadata, "model_dump"):
                metadata = metadata.model_dump(exclude_none=True)
            elif metadata is None:
                metadata = {}

            markdown = getattr(result, "markdown", None) or ""

            return {
                "url": url,
                "markdown": markdown[:5000],
                "metadata": metadata,
            }
        except Exception as e:
            logger.error(f"Firecrawl scrape error: {e}")
            return {"error": str(e)}
    
    def crawl(self, url: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Crawl a website."""
        if not url:
            return [{"error": "url is required"}]
        
        if not self.api_key:
            return [{"error": "FIRECRAWL_API_KEY not configured"}]
        
        try:
            # firecrawl-py v2 (>=4): kwargs instead of a params dict; returns a
            # typed CrawlJob whose `.data` is a list of Document objects.
            result = self.client.crawl(
                url,
                limit=limit,
                poll_interval=5,
            )

            data = getattr(result, "data", None) or []

            pages = []
            for page in data[:limit]:
                metadata = getattr(page, "metadata", None)
                pages.append({
                    "url": getattr(metadata, "source_url", None),
                    "title": getattr(metadata, "title", None),
                    "markdown": (getattr(page, "markdown", None) or "")[:2000],
                })
            return pages
        except Exception as e:
            logger.error(f"Firecrawl crawl error: {e}")
            return [{"error": str(e)}]


def firecrawl_scrape(url: str) -> Dict[str, Any]:
    """Scrape URL with Firecrawl."""
    return FirecrawlTool().scrape(url=url)
