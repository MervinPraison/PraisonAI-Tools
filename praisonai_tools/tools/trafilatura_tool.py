"""Trafilatura Tool for PraisonAI Agents.

Web scraping and text extraction.

Usage:
    from praisonai_tools import TrafilaturaTool
    
    traf = TrafilaturaTool()
    content = traf.extract("https://example.com")
"""

import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class TrafilaturaTool(BaseTool):
    """Tool for web content extraction."""
    
    name = "trafilatura"
    description = "Extract text content from web pages."
    
    def run(
        self,
        action: str = "extract",
        url: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "extract":
            return self.extract(url=url, **kwargs)
        return {"error": f"Unknown action: {action}"}
    
    def extract(self, url: str, include_comments: bool = False, include_tables: bool = True) -> Dict[str, Any]:
        """Extract content from URL."""
        if not url:
            return {"error": "url is required"}
        
        try:
            import trafilatura
        except ImportError:
            return {"error": "trafilatura not installed. Install with: pip install trafilatura"}
        
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return {"error": "Failed to download page"}
            
            text = trafilatura.extract(
                downloaded,
                include_comments=include_comments,
                include_tables=include_tables,
            )
            
            metadata = trafilatura.extract_metadata(downloaded)
            
            return {
                "text": text,
                "title": metadata.title if metadata else None,
                "author": metadata.author if metadata else None,
                "date": metadata.date if metadata else None,
                "url": url,
            }
        except Exception as e:
            logger.error(f"Trafilatura extract error: {e}")
            return {"error": str(e)}


def trafilatura_extract(url: str) -> Dict[str, Any]:
    """Extract content from URL."""
    return TrafilaturaTool().extract(url=url)
