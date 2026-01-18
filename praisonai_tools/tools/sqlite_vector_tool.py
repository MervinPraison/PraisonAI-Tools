"""SQLite Vector Store Tool for PraisonAI Agents.

Zero-dependency vector database using SQLite.

Usage:
    from praisonai_tools import SQLiteVectorTool
    
    store = SQLiteVectorTool(path="vectors.db")
    store.add(collection="docs", documents=["text"], embeddings=[[0.1, 0.2]], ids=["1"])
    results = store.query(collection="docs", query_embeddings=[[0.1, 0.2]], n_results=5)

Features:
    - Zero external dependencies (stdlib only)
    - Persistent storage
    - Multiple collections
    - Cosine similarity search
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SQLiteVectorTool(BaseTool):
    """Tool for SQLite-based vector storage (zero dependencies)."""
    
    name = "sqlite_vector"
    description = "Store and query vectors in SQLite. Zero external dependencies."
    
    def __init__(self, path: Optional[str] = None):
        """
        Initialize SQLite vector store.
        
        Args:
            path: Path to SQLite database file. Defaults to ~/.praisonai/vectors.db
        """
        if path is None:
            path = os.path.expanduser("~/.praisonai/vectors.db")
        self.path = os.path.expanduser(path)
        self._conn = None
        self._ensure_dir()
        super().__init__()
    
    def _ensure_dir(self):
        """Ensure directory exists."""
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
    
    @property
    def conn(self):
        """Lazy connection initialization."""
        if self._conn is None:
            import sqlite3
            self._conn = sqlite3.connect(self.path)
            self._conn.row_factory = sqlite3.Row
            self._init_schema()
        return self._conn
    
    def _init_schema(self):
        """Initialize database schema."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS collections (
                name TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS vectors (
                id TEXT,
                collection TEXT,
                document TEXT,
                embedding TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id, collection),
                FOREIGN KEY (collection) REFERENCES collections(name)
            );
            
            CREATE INDEX IF NOT EXISTS idx_vectors_collection ON vectors(collection);
        """)
        self.conn.commit()
    
    def run(
        self,
        action: str = "query",
        collection: Optional[str] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        documents: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        ids: Optional[List[str]] = None,
        n_results: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        """Run vector store action."""
        action = action.lower().replace("-", "_")
        
        if action == "query":
            return self.query(collection=collection, query_embeddings=query_embeddings, n_results=n_results)
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
        elif action == "count":
            return self.count(collection=collection)
        elif action == "clear":
            return self.clear(collection=collection)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def query(
        self,
        collection: str,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query similar documents using cosine similarity."""
        if not collection:
            return [{"error": "collection is required"}]
        if not query_embeddings:
            return [{"error": "query_embeddings required"}]
        
        try:
            cursor = self.conn.execute(
                "SELECT id, document, embedding, metadata FROM vectors WHERE collection = ?",
                (collection,)
            )
            rows = cursor.fetchall()
            
            if not rows:
                return []
            
            query_emb = query_embeddings[0]
            results = []
            
            for row in rows:
                stored_emb = json.loads(row["embedding"])
                similarity = self._cosine_similarity(query_emb, stored_emb)
                results.append({
                    "id": row["id"],
                    "document": row["document"],
                    "distance": 1 - similarity,  # Convert similarity to distance
                    "similarity": similarity,
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                })
            
            # Sort by similarity descending
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:n_results]
            
        except Exception as e:
            logger.error(f"SQLite vector query error: {e}")
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
        if not embeddings:
            return {"error": "embeddings are required"}
        
        try:
            # Ensure collection exists
            self.conn.execute(
                "INSERT OR IGNORE INTO collections (name) VALUES (?)",
                (collection,)
            )
            
            documents = documents or [""] * len(ids)
            metadatas = metadatas or [None] * len(ids)
            
            for i, id_ in enumerate(ids):
                self.conn.execute(
                    """INSERT OR REPLACE INTO vectors (id, collection, document, embedding, metadata)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        id_,
                        collection,
                        documents[i] if i < len(documents) else "",
                        json.dumps(embeddings[i]),
                        json.dumps(metadatas[i]) if metadatas[i] else None,
                    )
                )
            
            self.conn.commit()
            return {"success": True, "added_count": len(ids)}
            
        except Exception as e:
            logger.error(f"SQLite vector add error: {e}")
            return {"error": str(e)}
    
    def delete(self, collection: str, ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Delete documents by ID."""
        if not collection:
            return {"error": "collection is required"}
        
        try:
            if ids:
                placeholders = ",".join("?" * len(ids))
                cursor = self.conn.execute(
                    f"DELETE FROM vectors WHERE collection = ? AND id IN ({placeholders})",
                    [collection] + ids
                )
            else:
                cursor = self.conn.execute(
                    "DELETE FROM vectors WHERE collection = ?",
                    (collection,)
                )
            
            self.conn.commit()
            return {"success": True, "deleted": cursor.rowcount}
            
        except Exception as e:
            logger.error(f"SQLite vector delete error: {e}")
            return {"error": str(e)}
    
    def get(self, collection: str, ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get documents by ID."""
        if not collection:
            return [{"error": "collection is required"}]
        
        try:
            if ids:
                placeholders = ",".join("?" * len(ids))
                cursor = self.conn.execute(
                    f"SELECT id, document, metadata FROM vectors WHERE collection = ? AND id IN ({placeholders})",
                    [collection] + ids
                )
            else:
                cursor = self.conn.execute(
                    "SELECT id, document, metadata FROM vectors WHERE collection = ?",
                    (collection,)
                )
            
            return [
                {
                    "id": row["id"],
                    "document": row["document"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                }
                for row in cursor.fetchall()
            ]
            
        except Exception as e:
            logger.error(f"SQLite vector get error: {e}")
            return [{"error": str(e)}]
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections."""
        try:
            cursor = self.conn.execute("SELECT name FROM collections")
            return [{"name": row["name"]} for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"SQLite vector list_collections error: {e}")
            return [{"error": str(e)}]
    
    def create_collection(self, collection: str) -> Dict[str, Any]:
        """Create a collection."""
        if not collection:
            return {"error": "collection is required"}
        
        try:
            self.conn.execute(
                "INSERT OR IGNORE INTO collections (name) VALUES (?)",
                (collection,)
            )
            self.conn.commit()
            return {"success": True, "collection": collection}
        except Exception as e:
            logger.error(f"SQLite vector create_collection error: {e}")
            return {"error": str(e)}
    
    def count(self, collection: Optional[str] = None) -> Dict[str, Any]:
        """Count vectors in collection."""
        try:
            if collection:
                cursor = self.conn.execute(
                    "SELECT COUNT(*) as count FROM vectors WHERE collection = ?",
                    (collection,)
                )
            else:
                cursor = self.conn.execute("SELECT COUNT(*) as count FROM vectors")
            
            return {"count": cursor.fetchone()["count"]}
        except Exception as e:
            logger.error(f"SQLite vector count error: {e}")
            return {"error": str(e)}
    
    def clear(self, collection: Optional[str] = None) -> Dict[str, Any]:
        """Clear all vectors (or in a collection)."""
        try:
            if collection:
                self.conn.execute("DELETE FROM vectors WHERE collection = ?", (collection,))
            else:
                self.conn.execute("DELETE FROM vectors")
                self.conn.execute("DELETE FROM collections")
            
            self.conn.commit()
            return {"success": True}
        except Exception as e:
            logger.error(f"SQLite vector clear error: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# Convenience functions
def sqlite_vector_query(
    collection: str, 
    query_embeddings: List[List[float]], 
    n_results: int = 10,
    path: str = None
) -> List[Dict[str, Any]]:
    """Query SQLite vector store."""
    return SQLiteVectorTool(path=path).query(
        collection=collection, 
        query_embeddings=query_embeddings, 
        n_results=n_results
    )


def sqlite_vector_add(
    collection: str,
    documents: List[str],
    embeddings: List[List[float]],
    ids: List[str],
    path: str = None
) -> Dict[str, Any]:
    """Add to SQLite vector store."""
    return SQLiteVectorTool(path=path).add(
        collection=collection,
        documents=documents,
        embeddings=embeddings,
        ids=ids
    )
