"""Mem0 Tool for PraisonAI Agents.

Memory management using Mem0.

Usage:
    from praisonai_tools import Mem0Tool
    
    mem0 = Mem0Tool()
    mem0.add("User prefers dark mode")

Environment Variables:
    MEM0_API_KEY: Mem0 API key (optional for local)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class Mem0Tool(BaseTool):
    """Tool for Mem0 memory management."""
    
    name = "mem0"
    description = "Store and retrieve memories using Mem0."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MEM0_API_KEY")
        self._memory = None
        super().__init__()
    
    @property
    def memory(self):
        if self._memory is None:
            try:
                from mem0 import Memory
            except ImportError:
                raise ImportError("mem0ai not installed. Install with: pip install mem0ai")
            self._memory = Memory()
        return self._memory
    
    def run(
        self,
        action: str = "add",
        text: Optional[str] = None,
        user_id: str = "default",
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "add":
            return self.add(text=text, user_id=user_id)
        elif action == "search":
            return self.search(query=text, user_id=user_id)
        elif action == "get_all":
            return self.get_all(user_id=user_id)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def add(self, text: str, user_id: str = "default") -> Dict[str, Any]:
        """Add memory."""
        if not text:
            return {"error": "text is required"}
        
        try:
            result = self.memory.add(text, user_id=user_id)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Mem0 add error: {e}")
            return {"error": str(e)}
    
    def search(self, query: str, user_id: str = "default") -> List[Dict[str, Any]]:
        """Search memories."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            results = self.memory.search(query, user_id=user_id)
            return results
        except Exception as e:
            logger.error(f"Mem0 search error: {e}")
            return [{"error": str(e)}]
    
    def get_all(self, user_id: str = "default") -> List[Dict[str, Any]]:
        """Get all memories."""
        try:
            results = self.memory.get_all(user_id=user_id)
            return results
        except Exception as e:
            logger.error(f"Mem0 get_all error: {e}")
            return [{"error": str(e)}]


def mem0_add(text: str, user_id: str = "default") -> Dict[str, Any]:
    """Add memory to Mem0."""
    return Mem0Tool().add(text=text, user_id=user_id)
