"""Qdrant Vector DB Tool for PraisonAI Agents.

Vector database operations using Qdrant.

Usage:
    from praisonai_tools import QdrantTool
    
    qdrant = QdrantTool()
    results = qdrant.search(collection="my_collection", vector=[...])

Environment Variables:
    QDRANT_URL: Qdrant server URL
    QDRANT_API_KEY: Qdrant API key (optional for local)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class QdrantTool(BaseTool):
    """Tool for Qdrant vector database."""
    
    name = "qdrant"
    description = "Store and query vectors in Qdrant."
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
            except ImportError:
                raise ImportError("qdrant-client not installed. Install with: pip install qdrant-client")
            
            self._client = QdrantClient(url=self.url, api_key=self.api_key)
        return self._client
    
    def run(
        self,
        action: str = "search",
        collection: Optional[str] = None,
        vector: Optional[List[float]] = None,
        points: Optional[List[Dict]] = None,
        ids: Optional[List] = None,
        limit: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(collection=collection, vector=vector, limit=limit, **kwargs)
        elif action == "upsert":
            return self.upsert(collection=collection, points=points)
        elif action == "delete":
            return self.delete(collection=collection, ids=ids)
        elif action == "get_collection":
            return self.get_collection(collection=collection)
        elif action == "list_collections":
            return self.list_collections()
        elif action == "create_collection":
            return self.create_collection(collection=collection, **kwargs)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(
        self,
        collection: str,
        vector: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """Search similar vectors."""
        if not collection or not vector:
            return [{"error": "collection and vector are required"}]
        
        try:
            from qdrant_client.models import Filter
            
            search_params = {
                "collection_name": collection,
                "query_vector": vector,
                "limit": limit,
            }
            
            if filter_dict:
                search_params["query_filter"] = Filter(**filter_dict)
            
            results = self.client.search(**search_params)
            
            return [
                {
                    "id": str(r.id),
                    "score": r.score,
                    "payload": r.payload,
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Qdrant search error: {e}")
            return [{"error": str(e)}]
    
    def upsert(self, collection: str, points: List[Dict]) -> Dict[str, Any]:
        """Upsert points."""
        if not collection or not points:
            return {"error": "collection and points are required"}
        
        try:
            from qdrant_client.models import PointStruct
            
            point_structs = [
                PointStruct(
                    id=p["id"],
                    vector=p["vector"],
                    payload=p.get("payload", {}),
                )
                for p in points
            ]
            
            self.client.upsert(collection_name=collection, points=point_structs)
            return {"success": True, "upserted_count": len(points)}
        except Exception as e:
            logger.error(f"Qdrant upsert error: {e}")
            return {"error": str(e)}
    
    def delete(self, collection: str, ids: List) -> Dict[str, Any]:
        """Delete points by ID."""
        if not collection or not ids:
            return {"error": "collection and ids are required"}
        
        try:
            self.client.delete(collection_name=collection, points_selector=ids)
            return {"success": True, "deleted": len(ids)}
        except Exception as e:
            logger.error(f"Qdrant delete error: {e}")
            return {"error": str(e)}
    
    def get_collection(self, collection: str) -> Dict[str, Any]:
        """Get collection info."""
        if not collection:
            return {"error": "collection is required"}
        
        try:
            info = self.client.get_collection(collection)
            return {
                "name": collection,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": str(info.status),
            }
        except Exception as e:
            logger.error(f"Qdrant get_collection error: {e}")
            return {"error": str(e)}
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections."""
        try:
            collections = self.client.get_collections()
            return [{"name": c.name} for c in collections.collections]
        except Exception as e:
            logger.error(f"Qdrant list_collections error: {e}")
            return [{"error": str(e)}]
    
    def create_collection(self, collection: str, vector_size: int = 1536, distance: str = "Cosine") -> Dict[str, Any]:
        """Create a collection."""
        if not collection:
            return {"error": "collection is required"}
        
        try:
            from qdrant_client.models import VectorParams, Distance
            
            dist_map = {"Cosine": Distance.COSINE, "Euclidean": Distance.EUCLID, "Dot": Distance.DOT}
            
            self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=vector_size, distance=dist_map.get(distance, Distance.COSINE)),
            )
            return {"success": True, "collection": collection}
        except Exception as e:
            logger.error(f"Qdrant create_collection error: {e}")
            return {"error": str(e)}


def qdrant_search(collection: str, vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
    """Search Qdrant."""
    return QdrantTool().search(collection=collection, vector=vector, limit=limit)
