"""Weaviate Vector DB Tool for PraisonAI Agents.

Vector database operations using Weaviate.

Usage:
    from praisonai_tools import WeaviateTool
    
    weaviate = WeaviateTool()
    results = weaviate.search(class_name="Document", query="machine learning")

Environment Variables:
    WEAVIATE_URL: Weaviate server URL
    WEAVIATE_API_KEY: Weaviate API key (optional)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class WeaviateTool(BaseTool):
    """Tool for Weaviate vector database."""
    
    name = "weaviate"
    description = "Store and query vectors in Weaviate."
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.url = url or os.getenv("WEAVIATE_URL", "http://localhost:8080")
        self.api_key = api_key or os.getenv("WEAVIATE_API_KEY")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                import weaviate
            except ImportError:
                raise ImportError("weaviate-client not installed. Install with: pip install weaviate-client")
            
            if self.api_key:
                self._client = weaviate.Client(
                    url=self.url,
                    auth_client_secret=weaviate.AuthApiKey(api_key=self.api_key),
                )
            else:
                self._client = weaviate.Client(url=self.url)
        return self._client
    
    def run(
        self,
        action: str = "search",
        class_name: Optional[str] = None,
        query: Optional[str] = None,
        vector: Optional[List[float]] = None,
        data: Optional[Dict] = None,
        limit: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(class_name=class_name, query=query, limit=limit)
        elif action == "vector_search":
            return self.vector_search(class_name=class_name, vector=vector, limit=limit)
        elif action == "add":
            return self.add(class_name=class_name, data=data)
        elif action == "get_schema":
            return self.get_schema()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(self, class_name: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search with text query."""
        if not class_name or not query:
            return [{"error": "class_name and query are required"}]
        
        try:
            result = (
                self.client.query
                .get(class_name, ["*"])
                .with_near_text({"concepts": [query]})
                .with_limit(limit)
                .do()
            )
            
            data = result.get("data", {}).get("Get", {}).get(class_name, [])
            return data
        except Exception as e:
            logger.error(f"Weaviate search error: {e}")
            return [{"error": str(e)}]
    
    def vector_search(self, class_name: str, vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Search with vector."""
        if not class_name or not vector:
            return [{"error": "class_name and vector are required"}]
        
        try:
            result = (
                self.client.query
                .get(class_name, ["*"])
                .with_near_vector({"vector": vector})
                .with_limit(limit)
                .do()
            )
            
            data = result.get("data", {}).get("Get", {}).get(class_name, [])
            return data
        except Exception as e:
            logger.error(f"Weaviate vector_search error: {e}")
            return [{"error": str(e)}]
    
    def add(self, class_name: str, data: Dict) -> Dict[str, Any]:
        """Add object."""
        if not class_name or not data:
            return {"error": "class_name and data are required"}
        
        try:
            uuid = self.client.data_object.create(data, class_name)
            return {"success": True, "uuid": uuid}
        except Exception as e:
            logger.error(f"Weaviate add error: {e}")
            return {"error": str(e)}
    
    def get_schema(self) -> Dict[str, Any]:
        """Get schema."""
        try:
            return self.client.schema.get()
        except Exception as e:
            logger.error(f"Weaviate get_schema error: {e}")
            return {"error": str(e)}


def weaviate_search(class_name: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search Weaviate."""
    return WeaviateTool().search(class_name=class_name, query=query, limit=limit)
