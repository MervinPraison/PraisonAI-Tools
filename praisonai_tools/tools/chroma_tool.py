"""Chroma Vector DB Tool for PraisonAI Agents.

Vector database operations using ChromaDB.

Usage:
    from praisonai_tools import ChromaTool
    
    chroma = ChromaTool()
    chroma.add(collection="docs", documents=["text1", "text2"], ids=["1", "2"])

Environment Variables:
    CHROMA_HOST: Chroma server host (for client mode)
    CHROMA_PORT: Chroma server port
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ChromaTool(BaseTool):
    """Tool for ChromaDB vector database."""
    
    name = "chroma"
    description = "Store and query vectors in ChromaDB."
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        persist_directory: Optional[str] = None,
    ):
        self.host = host or os.getenv("CHROMA_HOST")
        self.port = port or int(os.getenv("CHROMA_PORT", "8000")) if os.getenv("CHROMA_PORT") else None
        self.persist_directory = persist_directory
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                import chromadb
            except ImportError:
                raise ImportError("chromadb not installed. Install with: pip install chromadb")
            
            if self.host and self.port:
                self._client = chromadb.HttpClient(host=self.host, port=self.port)
            elif self.persist_directory:
                self._client = chromadb.PersistentClient(path=self.persist_directory)
            else:
                self._client = chromadb.Client()
        return self._client
    
    def run(
        self,
        action: str = "query",
        collection: Optional[str] = None,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        documents: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        ids: Optional[List[str]] = None,
        n_results: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "query":
            return self.query(collection=collection, query_texts=query_texts, query_embeddings=query_embeddings, n_results=n_results)
        elif action == "add":
            return self.add(collection=collection, documents=documents, embeddings=embeddings, ids=ids, **kwargs)
        elif action == "delete":
            return self.delete(collection=collection, ids=ids)
        elif action == "get":
            return self.get(collection=collection, ids=ids)
        elif action == "list_collections":
            return self.list_collections()
        elif action == "create_collection":
            return self.create_collection(collection=collection)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def query(
        self,
        collection: str,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query similar documents."""
        if not collection:
            return [{"error": "collection is required"}]
        if not query_texts and not query_embeddings:
            return [{"error": "query_texts or query_embeddings required"}]
        
        try:
            coll = self.client.get_collection(collection)
            
            params = {"n_results": n_results}
            if query_texts:
                params["query_texts"] = query_texts
            if query_embeddings:
                params["query_embeddings"] = query_embeddings
            
            results = coll.query(**params)
            
            items = []
            for i, doc_id in enumerate(results.get("ids", [[]])[0]):
                items.append({
                    "id": doc_id,
                    "document": results.get("documents", [[]])[0][i] if results.get("documents") else None,
                    "distance": results.get("distances", [[]])[0][i] if results.get("distances") else None,
                    "metadata": results.get("metadatas", [[]])[0][i] if results.get("metadatas") else None,
                })
            return items
        except Exception as e:
            logger.error(f"Chroma query error: {e}")
            return [{"error": str(e)}]
    
    def add(
        self,
        collection: str,
        documents: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        ids: List[str] = None,
        metadatas: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Add documents to collection."""
        if not collection or not ids:
            return {"error": "collection and ids are required"}
        if not documents and not embeddings:
            return {"error": "documents or embeddings required"}
        
        try:
            coll = self.client.get_or_create_collection(collection)
            
            params = {"ids": ids}
            if documents:
                params["documents"] = documents
            if embeddings:
                params["embeddings"] = embeddings
            if metadatas:
                params["metadatas"] = metadatas
            
            coll.add(**params)
            return {"success": True, "added_count": len(ids)}
        except Exception as e:
            logger.error(f"Chroma add error: {e}")
            return {"error": str(e)}
    
    def delete(self, collection: str, ids: List[str]) -> Dict[str, Any]:
        """Delete documents by ID."""
        if not collection or not ids:
            return {"error": "collection and ids are required"}
        
        try:
            coll = self.client.get_collection(collection)
            coll.delete(ids=ids)
            return {"success": True, "deleted": len(ids)}
        except Exception as e:
            logger.error(f"Chroma delete error: {e}")
            return {"error": str(e)}
    
    def get(self, collection: str, ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get documents by ID."""
        if not collection:
            return [{"error": "collection is required"}]
        
        try:
            coll = self.client.get_collection(collection)
            results = coll.get(ids=ids) if ids else coll.get()
            
            items = []
            for i, doc_id in enumerate(results.get("ids", [])):
                items.append({
                    "id": doc_id,
                    "document": results.get("documents", [])[i] if results.get("documents") else None,
                    "metadata": results.get("metadatas", [])[i] if results.get("metadatas") else None,
                })
            return items
        except Exception as e:
            logger.error(f"Chroma get error: {e}")
            return [{"error": str(e)}]
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections."""
        try:
            collections = self.client.list_collections()
            return [{"name": c.name} for c in collections]
        except Exception as e:
            logger.error(f"Chroma list_collections error: {e}")
            return [{"error": str(e)}]
    
    def create_collection(self, collection: str) -> Dict[str, Any]:
        """Create a collection."""
        if not collection:
            return {"error": "collection is required"}
        
        try:
            self.client.create_collection(collection)
            return {"success": True, "collection": collection}
        except Exception as e:
            logger.error(f"Chroma create_collection error: {e}")
            return {"error": str(e)}


def chroma_query(collection: str, query_texts: List[str], n_results: int = 10) -> List[Dict[str, Any]]:
    """Query ChromaDB."""
    return ChromaTool().query(collection=collection, query_texts=query_texts, n_results=n_results)
