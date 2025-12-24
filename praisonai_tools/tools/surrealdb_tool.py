"""SurrealDB Tool for PraisonAI Agents.

SurrealDB database operations.

Usage:
    from praisonai_tools import SurrealDBTool
    
    sdb = SurrealDBTool()
    results = sdb.query("SELECT * FROM users")

Environment Variables:
    SURREALDB_URL: SurrealDB URL
    SURREALDB_USER: Username
    SURREALDB_PASSWORD: Password
    SURREALDB_NAMESPACE: Namespace
    SURREALDB_DATABASE: Database
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SurrealDBTool(BaseTool):
    """Tool for SurrealDB operations."""
    
    name = "surrealdb"
    description = "SurrealDB database operations."
    
    def __init__(
        self,
        url: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        namespace: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.url = url or os.getenv("SURREALDB_URL", "ws://localhost:8000/rpc")
        self.user = user or os.getenv("SURREALDB_USER", "root")
        self.password = password or os.getenv("SURREALDB_PASSWORD", "root")
        self.namespace = namespace or os.getenv("SURREALDB_NAMESPACE", "test")
        self.database = database or os.getenv("SURREALDB_DATABASE", "test")
        self._db = None
        super().__init__()
    
    def run(
        self,
        action: str = "query",
        sql: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "query":
            return self.query(sql=sql)
        elif action == "create":
            return self.create(table=kwargs.get("table"), data=kwargs.get("data"))
        elif action == "select":
            return self.select(table=kwargs.get("table"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SurrealQL query."""
        if not sql:
            return [{"error": "sql is required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            headers = {
                "Accept": "application/json",
                "NS": self.namespace,
                "DB": self.database,
            }
            http_url = self.url.replace("ws://", "http://").replace("/rpc", "/sql")
            resp = requests.post(
                http_url,
                headers=headers,
                auth=(self.user, self.password),
                data=sql,
                timeout=30,
            )
            return resp.json()
        except Exception as e:
            logger.error(f"SurrealDB query error: {e}")
            return [{"error": str(e)}]
    
    def create(self, table: str, data: Dict) -> Dict[str, Any]:
        """Create record."""
        if not table or not data:
            return {"error": "table and data are required"}
        
        import json
        sql = f"CREATE {table} CONTENT {json.dumps(data)}"
        result = self.query(sql)
        return result[0] if result else {"error": "Create failed"}
    
    def select(self, table: str) -> List[Dict[str, Any]]:
        """Select all from table."""
        if not table:
            return [{"error": "table is required"}]
        return self.query(f"SELECT * FROM {table}")


def surrealdb_query(sql: str) -> List[Dict[str, Any]]:
    """Query SurrealDB."""
    return SurrealDBTool().query(sql=sql)
