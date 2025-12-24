"""Firestore Tool for PraisonAI Agents.

Google Cloud Firestore operations.

Usage:
    from praisonai_tools import FirestoreTool
    
    fs = FirestoreTool()
    docs = fs.list_documents(collection="users")

Environment Variables:
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class FirestoreTool(BaseTool):
    """Tool for Firestore operations."""
    
    name = "firestore"
    description = "Google Cloud Firestore database operations."
    
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self._db = None
        super().__init__()
    
    @property
    def db(self):
        if self._db is None:
            try:
                from google.cloud import firestore
            except ImportError:
                raise ImportError("google-cloud-firestore not installed")
            self._db = firestore.Client(project=self.project_id)
        return self._db
    
    def run(
        self,
        action: str = "list",
        collection: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list":
            return self.list_documents(collection=collection, **kwargs)
        elif action == "get":
            return self.get_document(collection=collection, doc_id=kwargs.get("doc_id"))
        elif action == "add":
            return self.add_document(collection=collection, data=kwargs.get("data"))
        elif action == "update":
            return self.update_document(collection=collection, doc_id=kwargs.get("doc_id"), data=kwargs.get("data"))
        elif action == "delete":
            return self.delete_document(collection=collection, doc_id=kwargs.get("doc_id"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_documents(self, collection: str, limit: int = 100) -> List[Dict[str, Any]]:
        """List documents in collection."""
        if not collection:
            return [{"error": "collection is required"}]
        
        try:
            docs = self.db.collection(collection).limit(limit).stream()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"Firestore list error: {e}")
            return [{"error": str(e)}]
    
    def get_document(self, collection: str, doc_id: str) -> Dict[str, Any]:
        """Get document by ID."""
        if not collection or not doc_id:
            return {"error": "collection and doc_id are required"}
        
        try:
            doc = self.db.collection(collection).document(doc_id).get()
            if doc.exists:
                return {"id": doc.id, **doc.to_dict()}
            return {"error": "Document not found"}
        except Exception as e:
            logger.error(f"Firestore get error: {e}")
            return {"error": str(e)}
    
    def add_document(self, collection: str, data: Dict) -> Dict[str, Any]:
        """Add document."""
        if not collection or not data:
            return {"error": "collection and data are required"}
        
        try:
            _, doc_ref = self.db.collection(collection).add(data)
            return {"success": True, "id": doc_ref.id}
        except Exception as e:
            logger.error(f"Firestore add error: {e}")
            return {"error": str(e)}
    
    def update_document(self, collection: str, doc_id: str, data: Dict) -> Dict[str, Any]:
        """Update document."""
        if not collection or not doc_id or not data:
            return {"error": "collection, doc_id, and data are required"}
        
        try:
            self.db.collection(collection).document(doc_id).update(data)
            return {"success": True}
        except Exception as e:
            logger.error(f"Firestore update error: {e}")
            return {"error": str(e)}
    
    def delete_document(self, collection: str, doc_id: str) -> Dict[str, Any]:
        """Delete document."""
        if not collection or not doc_id:
            return {"error": "collection and doc_id are required"}
        
        try:
            self.db.collection(collection).document(doc_id).delete()
            return {"success": True}
        except Exception as e:
            logger.error(f"Firestore delete error: {e}")
            return {"error": str(e)}


def firestore_list(collection: str, limit: int = 100) -> List[Dict[str, Any]]:
    """List Firestore documents."""
    return FirestoreTool().list_documents(collection=collection, limit=limit)
