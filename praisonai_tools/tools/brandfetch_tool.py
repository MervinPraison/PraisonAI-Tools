"""Brandfetch Tool for PraisonAI Agents.

Get brand assets and information.

Usage:
    from praisonai_tools import BrandfetchTool
    
    bf = BrandfetchTool()
    brand = bf.get_brand("google.com")

Environment Variables:
    BRANDFETCH_API_KEY: Brandfetch API key
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class BrandfetchTool(BaseTool):
    """Tool for Brandfetch brand data."""
    
    name = "brandfetch"
    description = "Get brand assets and information."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BRANDFETCH_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "get_brand",
        domain: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "get_brand":
            return self.get_brand(domain=domain)
        return {"error": f"Unknown action: {action}"}
    
    def get_brand(self, domain: str) -> Dict[str, Any]:
        """Get brand information."""
        if not domain:
            return {"error": "domain is required"}
        if not self.api_key:
            return {"error": "BRANDFETCH_API_KEY required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(f"https://api.brandfetch.io/v2/brands/{domain}", headers=headers, timeout=10)
            return resp.json()
        except Exception as e:
            logger.error(f"Brandfetch error: {e}")
            return {"error": str(e)}


def brandfetch_get_brand(domain: str) -> Dict[str, Any]:
    """Get brand info."""
    return BrandfetchTool().get_brand(domain=domain)
