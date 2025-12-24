"""SingleStore Tool for PraisonAI Agents.

SingleStore database operations.

Usage:
    from praisonai_tools import SingleStoreTool
    
    ss = SingleStoreTool()
    results = ss.query("SELECT * FROM users LIMIT 10")

Environment Variables:
    SINGLESTORE_HOST: SingleStore host
    SINGLESTORE_PORT: SingleStore port
    SINGLESTORE_USER: Username
    SINGLESTORE_PASSWORD: Password
    SINGLESTORE_DATABASE: Database name
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SingleStoreTool(BaseTool):
    """Tool for SingleStore operations."""
    
    name = "singlestore"
    description = "SingleStore database operations."
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.host = host or os.getenv("SINGLESTORE_HOST", "localhost")
        self.port = port or int(os.getenv("SINGLESTORE_PORT", "3306"))
        self.user = user or os.getenv("SINGLESTORE_USER")
        self.password = password or os.getenv("SINGLESTORE_PASSWORD")
        self.database = database or os.getenv("SINGLESTORE_DATABASE")
        self._conn = None
        super().__init__()
    
    @property
    def conn(self):
        if self._conn is None:
            try:
                import pymysql
            except ImportError:
                raise ImportError("pymysql not installed. Install with: pip install pymysql")
            self._conn = pymysql.connect(
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
            logger.error(f"SingleStore query error: {e}")
            return [{"error": str(e)}]
    
    def execute(self, sql: str) -> Dict[str, Any]:
        """Execute SQL statement."""
        if not sql:
            return {"error": "sql is required"}
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql)
                self.conn.commit()
                return {"success": True, "affected_rows": cursor.rowcount}
        except Exception as e:
            logger.error(f"SingleStore execute error: {e}")
            return {"error": str(e)}
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """List tables."""
        return self.query("SHOW TABLES")


def singlestore_query(sql: str) -> List[Dict[str, Any]]:
    """Query SingleStore."""
    return SingleStoreTool().query(sql=sql)
