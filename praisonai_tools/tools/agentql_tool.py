"""AgentQL Tool for PraisonAI Agents.

Web scraping using AgentQL.

Usage:
    from praisonai_tools import AgentQLTool
    
    aql = AgentQLTool()
    content = aql.query("https://example.com", "{ products[] { name price } }")

Environment Variables:
    AGENTQL_API_KEY: AgentQL API key
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class AgentQLTool(BaseTool):
    """Tool for AgentQL web scraping."""
    
    name = "agentql"
    description = "Web scraping using AgentQL queries."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("AGENTQL_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "query",
        url: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "query":
            return self.query(url=url, query=query)
        return {"error": f"Unknown action: {action}"}
    
    def query(self, url: str, query: str) -> Dict[str, Any]:
        """Query webpage with AgentQL."""
        if not url or not query:
            return {"error": "url and query are required"}
        if not self.api_key:
            return {"error": "AGENTQL_API_KEY required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {"url": url, "query": query}
            resp = requests.post(
                "https://api.agentql.com/v1/query",
                headers=headers,
                json=data,
                timeout=60,
            )
            return resp.json()
        except Exception as e:
            logger.error(f"AgentQL query error: {e}")
            return {"error": str(e)}


def agentql_query(url: str, query: str) -> Dict[str, Any]:
    """Query with AgentQL."""
    return AgentQLTool().query(url=url, query=query)
