"""Redshift Tool for PraisonAI Agents.

AWS Redshift operations.

Usage:
    from praisonai_tools import RedshiftTool
    
    rs = RedshiftTool()
    results = rs.query("SELECT * FROM users LIMIT 10")

Environment Variables:
    REDSHIFT_HOST: Redshift host
    REDSHIFT_PORT: Redshift port
    REDSHIFT_USER: Username
    REDSHIFT_PASSWORD: Password
    REDSHIFT_DATABASE: Database name
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class RedshiftTool(BaseTool):
    """Tool for Redshift operations."""
    
    name = "redshift"
    description = "AWS Redshift database operations."
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.host = host or os.getenv("REDSHIFT_HOST")
        self.port = port or int(os.getenv("REDSHIFT_PORT", "5439"))
        self.user = user or os.getenv("REDSHIFT_USER")
        self.password = password or os.getenv("REDSHIFT_PASSWORD")
        self.database = database or os.getenv("REDSHIFT_DATABASE")
        self._conn = None
        super().__init__()
    
    @property
    def conn(self):
        if self._conn is None:
            try:
                import psycopg2
            except ImportError:
                raise ImportError("psycopg2 not installed")
            self._conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
            )
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
            with self.conn.cursor() as cursor:
                cursor.execute(sql)
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Redshift query error: {e}")
            return [{"error": str(e)}]
    
    def execute(self, sql: str) -> Dict[str, Any]:
        """Execute SQL statement."""
        if not sql:
            return {"error": "sql is required"}
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql)
                self.conn.commit()
                return {"success": True}
        except Exception as e:
            logger.error(f"Redshift execute error: {e}")
            return {"error": str(e)}
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """List tables."""
        sql = """
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        """
        return self.query(sql)


def redshift_query(sql: str) -> List[Dict[str, Any]]:
    """Query Redshift."""
    return RedshiftTool().query(sql=sql)
