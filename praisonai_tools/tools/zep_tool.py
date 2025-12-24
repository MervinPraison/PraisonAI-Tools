"""Zep Tool for PraisonAI Agents.

Memory management using Zep.

Usage:
    from praisonai_tools import ZepTool
    
    zep = ZepTool()
    zep.add_memory(session_id="user123", content="User likes coffee")

Environment Variables:
    ZEP_API_URL: Zep API URL
    ZEP_API_KEY: Zep API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ZepTool(BaseTool):
    """Tool for Zep memory management."""
    
    name = "zep"
    description = "Memory management using Zep."
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.api_url = api_url or os.getenv("ZEP_API_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("ZEP_API_KEY")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                from zep_python import ZepClient
            except ImportError:
                raise ImportError("zep-python not installed. Install with: pip install zep-python")
            self._client = ZepClient(base_url=self.api_url, api_key=self.api_key)
        return self._client
    
    def run(
        self,
        action: str = "add_memory",
        session_id: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "add_memory":
            return self.add_memory(session_id=session_id, content=kwargs.get("content"))
        elif action == "get_memory":
            return self.get_memory(session_id=session_id)
        elif action == "search_memory":
            return self.search_memory(session_id=session_id, query=kwargs.get("query"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def add_memory(self, session_id: str, content: str) -> Dict[str, Any]:
        """Add memory to session."""
        if not session_id or not content:
            return {"error": "session_id and content are required"}
        
        try:
            from zep_python import Memory, Message
            memory = Memory(messages=[Message(role="user", content=content)])
            self.client.memory.add_memory(session_id, memory)
            return {"success": True}
        except Exception as e:
            logger.error(f"Zep add_memory error: {e}")
            return {"error": str(e)}
    
    def get_memory(self, session_id: str) -> Dict[str, Any]:
        """Get memory for session."""
        if not session_id:
            return {"error": "session_id is required"}
        
        try:
            memory = self.client.memory.get_memory(session_id)
            return {"messages": [{"role": m.role, "content": m.content} for m in memory.messages]}
        except Exception as e:
            logger.error(f"Zep get_memory error: {e}")
            return {"error": str(e)}
    
    def search_memory(self, session_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search memory."""
        if not session_id or not query:
            return [{"error": "session_id and query are required"}]
        
        try:
            results = self.client.memory.search_memory(session_id, query, limit=limit)
            return [{"content": r.message.content, "score": r.score} for r in results]
        except Exception as e:
            logger.error(f"Zep search_memory error: {e}")
            return [{"error": str(e)}]


def zep_add_memory(session_id: str, content: str) -> Dict[str, Any]:
    """Add memory to Zep."""
    return ZepTool().add_memory(session_id=session_id, content=content)
