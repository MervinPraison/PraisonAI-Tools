"""Knowledge Tool for PraisonAI Agents.

Knowledge base operations with document storage and retrieval.

Usage:
    from praisonai_tools import KnowledgeTool
    
    kb = KnowledgeTool()
    kb.add_document("doc1", "This is some content about AI")
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class KnowledgeTool(BaseTool):
    """Tool for knowledge base operations."""
    
    name = "knowledge"
    description = "Knowledge base operations with document storage and retrieval."
    
    def __init__(self):
        self._documents = {}
        super().__init__()
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "add":
            return self.add_document(doc_id=kwargs.get("doc_id"), content=kwargs.get("content"), metadata=kwargs.get("metadata"))
        elif action == "search":
            return self.search(query=query, **kwargs)
        elif action == "get":
            return self.get_document(doc_id=kwargs.get("doc_id"))
        elif action == "delete":
            return self.delete_document(doc_id=kwargs.get("doc_id"))
        elif action == "list":
            return self.list_documents()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def add_document(self, doc_id: str, content: str, metadata: Dict = None) -> Dict[str, Any]:
        """Add document to knowledge base."""
        if not doc_id or not content:
            return {"error": "doc_id and content are required"}
        
        self._documents[doc_id] = {
            "content": content,
            "metadata": metadata or {},
        }
        return {"success": True, "doc_id": doc_id}
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search documents (simple text matching)."""
        if not query:
            return [{"error": "query is required"}]
        
        query_lower = query.lower()
        results = []
        
        for doc_id, doc in self._documents.items():
            content = doc["content"].lower()
            if query_lower in content:
                score = content.count(query_lower) / len(content.split())
                results.append({
                    "doc_id": doc_id,
                    "content": doc["content"][:500],
                    "metadata": doc["metadata"],
                    "score": score,
                })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """Get document by ID."""
        if not doc_id:
            return {"error": "doc_id is required"}
        
        if doc_id not in self._documents:
            return {"error": "Document not found"}
        
        doc = self._documents[doc_id]
        return {"doc_id": doc_id, "content": doc["content"], "metadata": doc["metadata"]}
    
    def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """Delete document."""
        if not doc_id:
            return {"error": "doc_id is required"}
        
        if doc_id not in self._documents:
            return {"error": "Document not found"}
        
        del self._documents[doc_id]
        return {"success": True}
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents."""
        return [
            {"doc_id": doc_id, "metadata": doc["metadata"], "content_length": len(doc["content"])}
            for doc_id, doc in self._documents.items()
        ]


def knowledge_search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search knowledge base."""
    return KnowledgeTool().search(query=query, limit=limit)
