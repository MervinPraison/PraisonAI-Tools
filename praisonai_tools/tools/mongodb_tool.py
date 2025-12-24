"""MongoDB Tool for PraisonAI Agents.

Interact with MongoDB databases.

Usage:
    from praisonai_tools import MongoDBTool
    
    mongo = MongoDBTool(uri="mongodb://localhost:27017", database="mydb")
    docs = mongo.find(collection="users", query={"active": True})

Environment Variables:
    MONGODB_URI: MongoDB connection URI
    MONGODB_DATABASE: Database name
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class MongoDBTool(BaseTool):
    """Tool for interacting with MongoDB."""
    
    name = "mongodb"
    description = "Query and manage MongoDB collections."
    
    def __init__(
        self,
        uri: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.database_name = database or os.getenv("MONGODB_DATABASE")
        self._client = None
        self._db = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                from pymongo import MongoClient
            except ImportError:
                raise ImportError("pymongo not installed. Install with: pip install pymongo")
            self._client = MongoClient(self.uri)
        return self._client
    
    @property
    def db(self):
        if self._db is None:
            if not self.database_name:
                raise ValueError("Database name required")
            self._db = self.client[self.database_name]
        return self._db
    
    def run(
        self,
        action: str = "find",
        collection: Optional[str] = None,
        query: Optional[Dict] = None,
        document: Optional[Dict] = None,
        limit: int = 100,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "find":
            return self.find(collection=collection, query=query, limit=limit)
        elif action == "find_one":
            return self.find_one(collection=collection, query=query)
        elif action == "insert_one":
            return self.insert_one(collection=collection, document=document)
        elif action == "insert_many":
            return self.insert_many(collection=collection, documents=kwargs.get("documents", []))
        elif action == "update_one":
            return self.update_one(collection=collection, query=query, update=kwargs.get("update", {}))
        elif action == "delete_one":
            return self.delete_one(collection=collection, query=query)
        elif action == "count":
            return self.count(collection=collection, query=query)
        elif action == "list_collections":
            return self.list_collections()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def find(self, collection: str, query: Optional[Dict] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Find documents."""
        if not collection:
            return [{"error": "collection is required"}]
        
        try:
            coll = self.db[collection]
            cursor = coll.find(query or {}).limit(limit)
            results = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                results.append(doc)
            return results
        except Exception as e:
            logger.error(f"MongoDB find error: {e}")
            return [{"error": str(e)}]
    
    def find_one(self, collection: str, query: Optional[Dict] = None) -> Dict[str, Any]:
        """Find one document."""
        if not collection:
            return {"error": "collection is required"}
        
        try:
            coll = self.db[collection]
            doc = coll.find_one(query or {})
            if doc:
                doc["_id"] = str(doc["_id"])
                return doc
            return {"error": "Document not found"}
        except Exception as e:
            logger.error(f"MongoDB find_one error: {e}")
            return {"error": str(e)}
    
    def insert_one(self, collection: str, document: Dict) -> Dict[str, Any]:
        """Insert one document."""
        if not collection:
            return {"error": "collection is required"}
        if not document:
            return {"error": "document is required"}
        
        try:
            coll = self.db[collection]
            result = coll.insert_one(document)
            return {"success": True, "inserted_id": str(result.inserted_id)}
        except Exception as e:
            logger.error(f"MongoDB insert_one error: {e}")
            return {"error": str(e)}
    
    def insert_many(self, collection: str, documents: List[Dict]) -> Dict[str, Any]:
        """Insert multiple documents."""
        if not collection:
            return {"error": "collection is required"}
        if not documents:
            return {"error": "documents is required"}
        
        try:
            coll = self.db[collection]
            result = coll.insert_many(documents)
            return {"success": True, "inserted_count": len(result.inserted_ids)}
        except Exception as e:
            logger.error(f"MongoDB insert_many error: {e}")
            return {"error": str(e)}
    
    def update_one(self, collection: str, query: Dict, update: Dict) -> Dict[str, Any]:
        """Update one document."""
        if not collection:
            return {"error": "collection is required"}
        if not query:
            return {"error": "query is required"}
        if not update:
            return {"error": "update is required"}
        
        try:
            coll = self.db[collection]
            result = coll.update_one(query, update)
            return {
                "success": True,
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
            }
        except Exception as e:
            logger.error(f"MongoDB update_one error: {e}")
            return {"error": str(e)}
    
    def delete_one(self, collection: str, query: Dict) -> Dict[str, Any]:
        """Delete one document."""
        if not collection:
            return {"error": "collection is required"}
        if not query:
            return {"error": "query is required"}
        
        try:
            coll = self.db[collection]
            result = coll.delete_one(query)
            return {"success": True, "deleted_count": result.deleted_count}
        except Exception as e:
            logger.error(f"MongoDB delete_one error: {e}")
            return {"error": str(e)}
    
    def count(self, collection: str, query: Optional[Dict] = None) -> Dict[str, Any]:
        """Count documents."""
        if not collection:
            return {"error": "collection is required"}
        
        try:
            coll = self.db[collection]
            count = coll.count_documents(query or {})
            return {"count": count}
        except Exception as e:
            logger.error(f"MongoDB count error: {e}")
            return {"error": str(e)}
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections."""
        try:
            names = self.db.list_collection_names()
            return [{"collection_name": name} for name in names]
        except Exception as e:
            logger.error(f"MongoDB list_collections error: {e}")
            return [{"error": str(e)}]


def query_mongodb(collection: str, query: Optional[Dict] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Query MongoDB collection."""
    return MongoDBTool().find(collection=collection, query=query, limit=limit)
