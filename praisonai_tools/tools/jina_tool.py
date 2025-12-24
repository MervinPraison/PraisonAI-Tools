"""Jina Reader Tool for PraisonAI Agents.

Read and extract content from URLs using Jina Reader.

Usage:
    from praisonai_tools import JinaTool
    
    jina = JinaTool()
    content = jina.read("https://example.com")

Environment Variables:
    JINA_API_KEY: Jina API key (optional for basic usage)
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class JinaTool(BaseTool):
    """Tool for reading web content using Jina Reader."""
    
    name = "jina"
    description = "Read and extract content from URLs using Jina Reader."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "read",
        url: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        action = action.lower().replace("-", "_")
        
        if action == "read":
            return self.read(url=url)
        elif action == "search":
            return self.search(query=query)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def read(self, url: str) -> Dict[str, Any]:
        """Read content from URL."""
        if not url:
            return {"error": "url is required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = requests.get(
                f"https://r.jina.ai/{url}",
                headers=headers,
                timeout=30,
            )
            
            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}"}
            
            return {
                "url": url,
                "content": response.text[:10000],
            }
        except Exception as e:
            logger.error(f"Jina read error: {e}")
            return {"error": str(e)}
    
    def search(self, query: str) -> Dict[str, Any]:
        """Search using Jina."""
        if not query:
            return {"error": "query is required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = requests.get(
                f"https://s.jina.ai/{query}",
                headers=headers,
                timeout=30,
            )
            
            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}"}
            
            return {
                "query": query,
                "content": response.text[:10000],
            }
        except Exception as e:
            logger.error(f"Jina search error: {e}")
            return {"error": str(e)}


def jina_read(url: str) -> Dict[str, Any]:
    """Read URL with Jina."""
    return JinaTool().read(url=url)
