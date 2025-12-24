"""PGVector Tool for PraisonAI Agents.

Vector operations using PostgreSQL with pgvector.

Usage:
    from praisonai_tools import PGVectorTool
    
    pgv = PGVectorTool()
    results = pgv.search(table="documents", vector=[...])

Environment Variables:
    PGVECTOR_HOST: PostgreSQL host
    PGVECTOR_PORT: PostgreSQL port
    PGVECTOR_USER: Username
    PGVECTOR_PASSWORD: Password
    PGVECTOR_DATABASE: Database name
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class PGVectorTool(BaseTool):
    """Tool for PGVector operations."""
    
    name = "pgvector"
    description = "Vector operations using PostgreSQL with pgvector."
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.host = host or os.getenv("PGVECTOR_HOST", "localhost")
        self.port = port or int(os.getenv("PGVECTOR_PORT", "5432"))
        self.user = user or os.getenv("PGVECTOR_USER")
        self.password = password or os.getenv("PGVECTOR_PASSWORD")
        self.database = database or os.getenv("PGVECTOR_DATABASE")
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
        action: str = "search",
        table: Optional[str] = None,
        vector: Optional[List[float]] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(table=table, vector=vector, **kwargs)
        elif action == "insert":
            return self.insert(table=table, vector=vector, **kwargs)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(self, table: str, vector: List[float], limit: int = 10, column: str = "embedding") -> List[Dict[str, Any]]:
        """Search by vector similarity."""
        if not table or not vector:
            return [{"error": "table and vector are required"}]
        
        try:
            with self.conn.cursor() as cursor:
                vector_str = "[" + ",".join(map(str, vector)) + "]"
                sql = f"SELECT *, {column} <-> %s::vector AS distance FROM {table} ORDER BY distance LIMIT %s"
                cursor.execute(sql, (vector_str, limit))
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"PGVector search error: {e}")
            return [{"error": str(e)}]
    
    def insert(self, table: str, vector: List[float], data: Dict = None, column: str = "embedding") -> Dict[str, Any]:
        """Insert vector."""
        if not table or not vector:
            return {"error": "table and vector are required"}
        
        try:
            with self.conn.cursor() as cursor:
                vector_str = "[" + ",".join(map(str, vector)) + "]"
                if data:
                    cols = list(data.keys()) + [column]
                    vals = list(data.values()) + [vector_str]
                    placeholders = ", ".join(["%s"] * len(vals))
                    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
                else:
                    sql = f"INSERT INTO {table} ({column}) VALUES (%s::vector)"
                    vals = [vector_str]
                cursor.execute(sql, vals)
                self.conn.commit()
                return {"success": True}
        except Exception as e:
            logger.error(f"PGVector insert error: {e}")
            return {"error": str(e)}


def pgvector_search(table: str, vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
    """Search PGVector."""
    return PGVectorTool().search(table=table, vector=vector, limit=limit)
