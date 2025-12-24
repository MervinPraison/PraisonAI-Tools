"""DuckDB Tool for PraisonAI Agents.

Execute SQL queries on DuckDB.

Usage:
    from praisonai_tools import DuckDBTool
    
    duckdb = DuckDBTool()
    results = duckdb.query("SELECT * FROM 'data.parquet'")
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class DuckDBTool(BaseTool):
    """Tool for DuckDB analytics."""
    
    name = "duckdb"
    description = "Execute SQL queries on DuckDB for analytics."
    
    def __init__(self, database: str = ":memory:"):
        self.database = database
        self._conn = None
        super().__init__()
    
    @property
    def conn(self):
        if self._conn is None:
            try:
                import duckdb
            except ImportError:
                raise ImportError("duckdb not installed. Install with: pip install duckdb")
            self._conn = duckdb.connect(self.database)
        return self._conn
    
    def run(
        self,
        action: str = "query",
        sql: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "query":
            return self.query(sql=sql)
        elif action == "execute":
            return self.execute(sql=sql)
        elif action == "list_tables":
            return self.list_tables()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL query."""
        if not sql:
            return [{"error": "sql is required"}]
        
        try:
            result = self.conn.execute(sql).fetchdf()
            return result.to_dict(orient="records")
        except Exception as e:
            logger.error(f"DuckDB query error: {e}")
            return [{"error": str(e)}]
    
    def execute(self, sql: str) -> Dict[str, Any]:
        """Execute SQL statement."""
        if not sql:
            return {"error": "sql is required"}
        
        try:
            self.conn.execute(sql)
            return {"success": True}
        except Exception as e:
            logger.error(f"DuckDB execute error: {e}")
            return {"error": str(e)}
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """List tables."""
        try:
            result = self.conn.execute("SHOW TABLES").fetchall()
            return [{"table_name": r[0]} for r in result]
        except Exception as e:
            logger.error(f"DuckDB list_tables error: {e}")
            return [{"error": str(e)}]


def duckdb_query(sql: str) -> List[Dict[str, Any]]:
    """Query DuckDB."""
    return DuckDBTool().query(sql=sql)
