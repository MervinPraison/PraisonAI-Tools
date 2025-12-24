"""LanceDB Vector DB Tool for PraisonAI Agents.

Vector database operations using LanceDB.

Usage:
    from praisonai_tools import LanceDBTool
    
    lancedb = LanceDBTool()
    results = lancedb.search(table="docs", query="machine learning")
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class LanceDBTool(BaseTool):
    """Tool for LanceDB vector database."""
    
    name = "lancedb"
    description = "Store and query vectors in LanceDB."
    
    def __init__(self, uri: str = "~/.lancedb"):
        self.uri = uri
        self._db = None
        super().__init__()
    
    @property
    def db(self):
        if self._db is None:
            try:
                import lancedb
            except ImportError:
                raise ImportError("lancedb not installed. Install with: pip install lancedb")
            self._db = lancedb.connect(self.uri)
        return self._db
    
    def run(
        self,
        action: str = "search",
        table: Optional[str] = None,
        query: Optional[str] = None,
        vector: Optional[List[float]] = None,
        data: Optional[List[Dict]] = None,
        limit: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(table=table, query=query, vector=vector, limit=limit)
        elif action == "add":
            return self.add(table=table, data=data)
        elif action == "list_tables":
            return self.list_tables()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(
        self,
        table: str,
        query: Optional[str] = None,
        vector: Optional[List[float]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search table."""
        if not table:
            return [{"error": "table is required"}]
        if not query and not vector:
            return [{"error": "query or vector is required"}]
        
        try:
            tbl = self.db.open_table(table)
            
            if vector:
                results = tbl.search(vector).limit(limit).to_list()
            else:
                results = tbl.search(query).limit(limit).to_list()
            
            return results
        except Exception as e:
            logger.error(f"LanceDB search error: {e}")
            return [{"error": str(e)}]
    
    def add(self, table: str, data: List[Dict]) -> Dict[str, Any]:
        """Add data to table."""
        if not table or not data:
            return {"error": "table and data are required"}
        
        try:
            if table in self.db.table_names():
                tbl = self.db.open_table(table)
                tbl.add(data)
            else:
                self.db.create_table(table, data)
            return {"success": True, "added": len(data)}
        except Exception as e:
            logger.error(f"LanceDB add error: {e}")
            return {"error": str(e)}
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """List tables."""
        try:
            tables = self.db.table_names()
            return [{"table_name": t} for t in tables]
        except Exception as e:
            logger.error(f"LanceDB list_tables error: {e}")
            return [{"error": str(e)}]


def lancedb_search(table: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search LanceDB."""
    return LanceDBTool().search(table=table, query=query, limit=limit)
