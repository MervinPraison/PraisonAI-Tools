"""Apify Tool for PraisonAI Agents.

Run web scraping actors on Apify.

Usage:
    from praisonai_tools import ApifyTool
    
    apify = ApifyTool()
    results = apify.run_actor("apify/web-scraper", {"startUrls": [{"url": "https://example.com"}]})

Environment Variables:
    APIFY_API_TOKEN: Apify API token
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ApifyTool(BaseTool):
    """Tool for Apify web scraping."""
    
    name = "apify"
    description = "Run web scraping actors on Apify."
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("APIFY_API_TOKEN")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                from apify_client import ApifyClient
            except ImportError:
                raise ImportError("apify-client not installed. Install with: pip install apify-client")
            if not self.api_token:
                raise ValueError("APIFY_API_TOKEN required")
            self._client = ApifyClient(self.api_token)
        return self._client
    
    def run(
        self,
        action: str = "run_actor",
        actor_id: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        if action == "run_actor":
            return self.run_actor(actor_id=actor_id, input_data=kwargs.get("input_data", {}))
        elif action == "get_dataset":
            return self.get_dataset(dataset_id=kwargs.get("dataset_id"))
        return {"error": f"Unknown action: {action}"}
    
    def run_actor(self, actor_id: str, input_data: Dict = None) -> List[Dict[str, Any]]:
        """Run an actor."""
        if not actor_id:
            return [{"error": "actor_id is required"}]
        
        try:
            run = self.client.actor(actor_id).call(run_input=input_data or {})
            dataset = self.client.dataset(run["defaultDatasetId"])
            items = list(dataset.iterate_items())
            return items
        except Exception as e:
            logger.error(f"Apify run_actor error: {e}")
            return [{"error": str(e)}]
    
    def get_dataset(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Get dataset items."""
        if not dataset_id:
            return [{"error": "dataset_id is required"}]
        
        try:
            dataset = self.client.dataset(dataset_id)
            items = list(dataset.iterate_items())
            return items
        except Exception as e:
            logger.error(f"Apify get_dataset error: {e}")
            return [{"error": str(e)}]


def apify_run_actor(actor_id: str, input_data: Dict = None) -> List[Dict[str, Any]]:
    """Run Apify actor."""
    return ApifyTool().run_actor(actor_id=actor_id, input_data=input_data)
