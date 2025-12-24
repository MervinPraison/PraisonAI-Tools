"""Milvus Vector DB Tool for PraisonAI Agents.

Vector database operations using Milvus.

Usage:
    from praisonai_tools import MilvusTool
    
    milvus = MilvusTool()
    results = milvus.search(collection="docs", vector=[...])

Environment Variables:
    MILVUS_HOST: Milvus server host
    MILVUS_PORT: Milvus server port
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class MilvusTool(BaseTool):
    """Tool for Milvus vector database."""
    
    name = "milvus"
    description = "Store and query vectors in Milvus."
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        uri: Optional[str] = None,
    ):
        self.host = host or os.getenv("MILVUS_HOST", "localhost")
        self.port = port or int(os.getenv("MILVUS_PORT", "19530"))
        self.uri = uri or os.getenv("MILVUS_URI")
        self._connected = False
        super().__init__()
    
    def _connect(self):
        if not self._connected:
            try:
                from pymilvus import connections
            except ImportError:
                raise ImportError("pymilvus not installed. Install with: pip install pymilvus")
            
            if self.uri:
                connections.connect(uri=self.uri)
            else:
                connections.connect(host=self.host, port=self.port)
            self._connected = True
    
    def run(
        self,
        action: str = "search",
        collection: Optional[str] = None,
        vector: Optional[List[float]] = None,
        data: Optional[List[Dict]] = None,
        limit: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(collection=collection, vector=vector, limit=limit)
        elif action == "insert":
            return self.insert(collection=collection, data=data)
        elif action == "list_collections":
            return self.list_collections()
        elif action == "get_collection_info":
            return self.get_collection_info(collection=collection)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(self, collection: str, vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Search vectors."""
        if not collection or not vector:
            return [{"error": "collection and vector are required"}]
        
        try:
            from pymilvus import Collection
            self._connect()
            
            coll = Collection(collection)
            coll.load()
            
            results = coll.search(
                data=[vector],
                anns_field="vector",
                param={"metric_type": "L2", "params": {"nprobe": 10}},
                limit=limit,
                output_fields=["*"],
            )
            
            items = []
            for hits in results:
                for hit in hits:
                    items.append({
                        "id": hit.id,
                        "distance": hit.distance,
                        "entity": hit.entity.to_dict() if hasattr(hit.entity, "to_dict") else {},
                    })
            return items
        except Exception as e:
            logger.error(f"Milvus search error: {e}")
            return [{"error": str(e)}]
    
    def insert(self, collection: str, data: List[Dict]) -> Dict[str, Any]:
        """Insert data."""
        if not collection or not data:
            return {"error": "collection and data are required"}
        
        try:
            from pymilvus import Collection
            self._connect()
            
            coll = Collection(collection)
            result = coll.insert(data)
            return {"success": True, "insert_count": result.insert_count}
        except Exception as e:
            logger.error(f"Milvus insert error: {e}")
            return {"error": str(e)}
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """List collections."""
        try:
            from pymilvus import utility
            self._connect()
            
            collections = utility.list_collections()
            return [{"collection_name": c} for c in collections]
        except Exception as e:
            logger.error(f"Milvus list_collections error: {e}")
            return [{"error": str(e)}]
    
    def get_collection_info(self, collection: str) -> Dict[str, Any]:
        """Get collection info."""
        if not collection:
            return {"error": "collection is required"}
        
        try:
            from pymilvus import Collection
            self._connect()
            
            coll = Collection(collection)
            return {
                "name": collection,
                "num_entities": coll.num_entities,
                "schema": str(coll.schema),
            }
        except Exception as e:
            logger.error(f"Milvus get_collection_info error: {e}")
            return {"error": str(e)}


def milvus_search(collection: str, vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
    """Search Milvus."""
    return MilvusTool().search(collection=collection, vector=vector, limit=limit)
