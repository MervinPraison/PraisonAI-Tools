"""Supabase Tool for PraisonAI Agents.

Interact with Supabase database and storage.

Usage:
    from praisonai_tools import SupabaseTool
    
    supabase = SupabaseTool()
    data = supabase.select(table="users")

Environment Variables:
    SUPABASE_URL: Supabase project URL
    SUPABASE_KEY: Supabase API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SupabaseTool(BaseTool):
    """Tool for Supabase database operations."""
    
    name = "supabase"
    description = "Query and manage Supabase database."
    
    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
    ):
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_KEY")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                from supabase import create_client
            except ImportError:
                raise ImportError("supabase not installed. Install with: pip install supabase")
            
            if not self.url or not self.key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY required")
            
            self._client = create_client(self.url, self.key)
        return self._client
    
    def run(
        self,
        action: str = "select",
        table: Optional[str] = None,
        data: Optional[Dict] = None,
        query: Optional[Dict] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "select":
            return self.select(table=table, query=query, **kwargs)
        elif action == "insert":
            return self.insert(table=table, data=data)
        elif action == "update":
            return self.update(table=table, data=data, query=query)
        elif action == "delete":
            return self.delete(table=table, query=query)
        elif action == "rpc":
            return self.rpc(function=kwargs.get("function"), params=kwargs.get("params"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def select(self, table: str, query: Optional[Dict] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Select from table."""
        if not table:
            return [{"error": "table is required"}]
        
        try:
            q = self.client.table(table).select("*")
            
            if query:
                for key, value in query.items():
                    q = q.eq(key, value)
            
            result = q.limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error(f"Supabase select error: {e}")
            return [{"error": str(e)}]
    
    def insert(self, table: str, data: Dict) -> Dict[str, Any]:
        """Insert into table."""
        if not table or not data:
            return {"error": "table and data are required"}
        
        try:
            result = self.client.table(table).insert(data).execute()
            return {"success": True, "data": result.data}
        except Exception as e:
            logger.error(f"Supabase insert error: {e}")
            return {"error": str(e)}
    
    def update(self, table: str, data: Dict, query: Dict) -> Dict[str, Any]:
        """Update table."""
        if not table or not data or not query:
            return {"error": "table, data, and query are required"}
        
        try:
            q = self.client.table(table).update(data)
            for key, value in query.items():
                q = q.eq(key, value)
            result = q.execute()
            return {"success": True, "data": result.data}
        except Exception as e:
            logger.error(f"Supabase update error: {e}")
            return {"error": str(e)}
    
    def delete(self, table: str, query: Dict) -> Dict[str, Any]:
        """Delete from table."""
        if not table or not query:
            return {"error": "table and query are required"}
        
        try:
            q = self.client.table(table).delete()
            for key, value in query.items():
                q = q.eq(key, value)
            result = q.execute()
            return {"success": True, "deleted": len(result.data)}
        except Exception as e:
            logger.error(f"Supabase delete error: {e}")
            return {"error": str(e)}
    
    def rpc(self, function: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Call RPC function."""
        if not function:
            return {"error": "function is required"}
        
        try:
            result = self.client.rpc(function, params or {}).execute()
            return {"data": result.data}
        except Exception as e:
            logger.error(f"Supabase rpc error: {e}")
            return {"error": str(e)}


def supabase_select(table: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Select from Supabase."""
    return SupabaseTool().select(table=table, limit=limit)
