"""SQLite Tool for PraisonAI Agents.

Execute queries on SQLite databases.

Usage:
    from praisonai_tools import SQLiteTool
    
    sqlite = SQLiteTool(database="mydb.sqlite")
    results = sqlite.query("SELECT * FROM users LIMIT 10")

Environment Variables:
    SQLITE_DATABASE: Path to SQLite database file
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SQLiteTool(BaseTool):
    """Tool for interacting with SQLite databases."""
    
    name = "sqlite"
    description = "Execute SQL queries on SQLite databases."
    
    def __init__(self, database: Optional[str] = None):
        self.database = database or os.getenv("SQLITE_DATABASE", ":memory:")
        self._conn = None
        super().__init__()
    
    def _get_connection(self):
        """Get database connection."""
        import sqlite3
        
        if self._conn is None:
            self._conn = sqlite3.connect(self.database)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def run(
        self,
        action: str = "query",
        sql: Optional[str] = None,
        table: Optional[str] = None,
        limit: int = 100,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "query":
            return self.query(sql=sql, limit=limit)
        elif action == "list_tables":
            return self.list_tables()
        elif action == "describe_table":
            return self.describe_table(table=table)
        elif action == "execute":
            return self.execute(sql=sql)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def query(self, sql: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Execute SELECT query."""
        if not sql:
            return [{"error": "SQL query is required"}]
        
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith("SELECT"):
            return [{"error": "Only SELECT queries allowed."}]
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if "LIMIT" not in sql_upper:
                sql = f"{sql.rstrip(';')} LIMIT {limit}"
            
            cursor.execute(sql)
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"SQLite query error: {e}")
            return [{"error": str(e)}]
    
    def execute(self, sql: str) -> Dict[str, Any]:
        """Execute SQL statement."""
        if not sql:
            return {"error": "SQL statement is required"}
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(sql)
            rowcount = cursor.rowcount
            conn.commit()
            cursor.close()
            return {"success": True, "rows_affected": rowcount}
        except Exception as e:
            logger.error(f"SQLite execute error: {e}")
            return {"error": str(e)}
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """List all tables."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            rows = cursor.fetchall()
            cursor.close()
            return [{"table_name": row["name"]} for row in rows]
        except Exception as e:
            logger.error(f"SQLite list_tables error: {e}")
            return [{"error": str(e)}]
    
    def describe_table(self, table: str) -> Dict[str, Any]:
        """Get table schema."""
        if not table:
            return {"error": "table name is required"}
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            rows = cursor.fetchall()
            cursor.close()
            
            if not rows:
                return {"error": f"Table '{table}' not found"}
            
            columns = []
            for row in rows:
                columns.append({
                    "name": row["name"],
                    "type": row["type"],
                    "nullable": not row["notnull"],
                    "primary_key": bool(row["pk"]),
                    "default": row["dflt_value"],
                })
            
            return {"table": table, "columns": columns}
        except Exception as e:
            logger.error(f"SQLite describe_table error: {e}")
            return {"error": str(e)}
    
    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


def query_sqlite(sql: str, database: str = ":memory:") -> List[Dict[str, Any]]:
    """Execute SQLite query."""
    return SQLiteTool(database=database).query(sql=sql)
