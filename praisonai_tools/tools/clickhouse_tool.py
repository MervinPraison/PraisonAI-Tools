"""ClickHouse Tool for PraisonAI Agents.

ClickHouse database operations.

Usage:
    from praisonai_tools import ClickHouseTool
    
    ch = ClickHouseTool()
    results = ch.query("SELECT * FROM users LIMIT 10")

Environment Variables:
    CLICKHOUSE_HOST: ClickHouse host
    CLICKHOUSE_PORT: ClickHouse port
    CLICKHOUSE_USER: Username
    CLICKHOUSE_PASSWORD: Password
    CLICKHOUSE_DATABASE: Database name
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ClickHouseTool(BaseTool):
    """Tool for ClickHouse operations."""
    
    name = "clickhouse"
    description = "ClickHouse database operations."
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.host = host or os.getenv("CLICKHOUSE_HOST", "localhost")
        self.port = port or int(os.getenv("CLICKHOUSE_PORT", "9000"))
        self.user = user or os.getenv("CLICKHOUSE_USER", "default")
        self.password = password or os.getenv("CLICKHOUSE_PASSWORD", "")
        self.database = database or os.getenv("CLICKHOUSE_DATABASE", "default")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                from clickhouse_driver import Client
            except ImportError:
                raise ImportError("clickhouse-driver not installed")
            self._client = Client(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
            )
        return self._client
    
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
            result = self.client.execute(sql, with_column_types=True)
            rows, columns = result
            col_names = [c[0] for c in columns]
            return [dict(zip(col_names, row)) for row in rows]
        except Exception as e:
            logger.error(f"ClickHouse query error: {e}")
            return [{"error": str(e)}]
    
    def execute(self, sql: str) -> Dict[str, Any]:
        """Execute SQL statement."""
        if not sql:
            return {"error": "sql is required"}
        
        try:
            self.client.execute(sql)
            return {"success": True}
        except Exception as e:
            logger.error(f"ClickHouse execute error: {e}")
            return {"error": str(e)}
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """List tables."""
        return self.query("SHOW TABLES")


def clickhouse_query(sql: str) -> List[Dict[str, Any]]:
    """Query ClickHouse."""
    return ClickHouseTool().query(sql=sql)
