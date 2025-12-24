"""Pinecone Vector DB Tool for PraisonAI Agents.

Vector database operations using Pinecone.

Usage:
    from praisonai_tools import PineconeTool
    
    pc = PineconeTool()
    pc.upsert(vectors=[{"id": "1", "values": [...], "metadata": {...}}])

Environment Variables:
    PINECONE_API_KEY: Pinecone API key
    PINECONE_INDEX: Default index name
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class PineconeTool(BaseTool):
    """Tool for Pinecone vector database."""
    
    name = "pinecone"
    description = "Store and query vectors in Pinecone."
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.index_name = index_name or os.getenv("PINECONE_INDEX")
        self._client = None
        self._index = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                from pinecone import Pinecone
            except ImportError:
                raise ImportError("pinecone-client not installed. Install with: pip install pinecone-client")
            
            if not self.api_key:
                raise ValueError("PINECONE_API_KEY required")
            
            self._client = Pinecone(api_key=self.api_key)
        return self._client
    
    @property
    def index(self):
        if self._index is None:
            if not self.index_name:
                raise ValueError("index_name required")
            self._index = self.client.Index(self.index_name)
        return self._index
    
    def run(
        self,
        action: str = "query",
        vector: Optional[List[float]] = None,
        vectors: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
        top_k: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "query":
            return self.query(vector=vector, top_k=top_k, **kwargs)
        elif action == "upsert":
            return self.upsert(vectors=vectors)
        elif action == "delete":
            return self.delete(ids=ids)
        elif action == "describe_index":
            return self.describe_index()
        elif action == "list_indexes":
            return self.list_indexes()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        include_metadata: bool = True,
        filter_dict: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """Query similar vectors."""
        if not vector:
            return [{"error": "vector is required"}]
        
        try:
            params = {
                "vector": vector,
                "top_k": top_k,
                "include_metadata": include_metadata,
            }
            if filter_dict:
                params["filter"] = filter_dict
            
            result = self.index.query(**params)
            
            matches = []
            for match in result.get("matches", []):
                matches.append({
                    "id": match["id"],
                    "score": match["score"],
                    "metadata": match.get("metadata", {}),
                })
            return matches
        except Exception as e:
            logger.error(f"Pinecone query error: {e}")
            return [{"error": str(e)}]
    
    def upsert(self, vectors: List[Dict]) -> Dict[str, Any]:
        """Upsert vectors."""
        if not vectors:
            return {"error": "vectors is required"}
        
        try:
            result = self.index.upsert(vectors=vectors)
            return {"success": True, "upserted_count": result.get("upserted_count")}
        except Exception as e:
            logger.error(f"Pinecone upsert error: {e}")
            return {"error": str(e)}
    
    def delete(self, ids: List[str]) -> Dict[str, Any]:
        """Delete vectors by ID."""
        if not ids:
            return {"error": "ids is required"}
        
        try:
            self.index.delete(ids=ids)
            return {"success": True, "deleted": len(ids)}
        except Exception as e:
            logger.error(f"Pinecone delete error: {e}")
            return {"error": str(e)}
    
    def describe_index(self) -> Dict[str, Any]:
        """Get index stats."""
        try:
            stats = self.index.describe_index_stats()
            return {
                "dimension": stats.get("dimension"),
                "total_vector_count": stats.get("total_vector_count"),
                "namespaces": stats.get("namespaces", {}),
            }
        except Exception as e:
            logger.error(f"Pinecone describe_index error: {e}")
            return {"error": str(e)}
    
    def list_indexes(self) -> List[Dict[str, Any]]:
        """List all indexes."""
        try:
            indexes = self.client.list_indexes()
            return [{"name": idx.name, "dimension": idx.dimension} for idx in indexes]
        except Exception as e:
            logger.error(f"Pinecone list_indexes error: {e}")
            return [{"error": str(e)}]


def pinecone_query(vector: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
    """Query Pinecone."""
    return PineconeTool().query(vector=vector, top_k=top_k)
