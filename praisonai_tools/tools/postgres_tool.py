"""PostgreSQL Tool for PraisonAI Agents.

Execute queries and interact with PostgreSQL databases.

Usage:
    from praisonai_tools import PostgresTool
    
    pg = PostgresTool(
        host="localhost",
        database="mydb",
        user="user",
        password="pass"
    )
    
    # Execute query
    results = pg.query("SELECT * FROM users LIMIT 10")
    
    # Get table info
    tables = pg.list_tables()

Environment Variables:
    POSTGRES_HOST: Database host
    POSTGRES_PORT: Database port (default: 5432)
    POSTGRES_DATABASE: Database name
    POSTGRES_USER: Username
    POSTGRES_PASSWORD: Password
    DATABASE_URL: Full connection URL (alternative)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class PostgresTool(BaseTool):
    """Tool for interacting with PostgreSQL databases."""
    
    name = "postgres"
    description = "Execute SQL queries on PostgreSQL databases."
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database_url: Optional[str] = None,
    ):
        """Initialize PostgresTool.
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Username
            password: Password
            database_url: Full connection URL (overrides other params)
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.host = host or os.getenv("POSTGRES_HOST", "localhost")
        self.port = port or int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = database or os.getenv("POSTGRES_DATABASE")
        self.user = user or os.getenv("POSTGRES_USER")
        self.password = password or os.getenv("POSTGRES_PASSWORD")
        self._conn = None
        super().__init__()
    
    def _get_connection(self):
        """Get database connection."""
        try:
            import psycopg2
        except ImportError:
            raise ImportError("psycopg2 not installed. Install with: pip install psycopg2-binary")
        
        if self._conn is None or self._conn.closed:
            if self.database_url:
                self._conn = psycopg2.connect(self.database_url)
            else:
                if not all([self.host, self.database, self.user]):
                    raise ValueError("Database connection parameters required")
                self._conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                )
        return self._conn
    
    def run(
        self,
        action: str = "query",
        sql: Optional[str] = None,
        table: Optional[str] = None,
        limit: int = 100,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        """Execute database action.
        
        Args:
            action: "query", "list_tables", "describe_table", "insert"
            sql: SQL query to execute
            table: Table name for describe/insert
            limit: Max rows to return
        """
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
        """Execute SELECT query and return results.
        
        Args:
            sql: SQL SELECT query
            limit: Max rows to return
            
        Returns:
            List of row dicts
        """
        if not sql:
            return [{"error": "SQL query is required"}]
        
        # Safety check - only allow SELECT
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith("SELECT"):
            return [{"error": "Only SELECT queries allowed. Use execute() for other statements."}]
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Add LIMIT if not present
            if "LIMIT" not in sql_upper:
                sql = f"{sql.rstrip(';')} LIMIT {limit}"
            
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"PostgreSQL query error: {e}")
            return [{"error": str(e)}]
    
    def execute(self, sql: str) -> Dict[str, Any]:
        """Execute SQL statement (INSERT, UPDATE, DELETE, etc).
        
        Args:
            sql: SQL statement
            
        Returns:
            Execution result
        """
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
            logger.error(f"PostgreSQL execute error: {e}")
            if self._conn:
                self._conn.rollback()
            return {"error": str(e)}
    
    def list_tables(self, schema: str = "public") -> List[Dict[str, Any]]:
        """List all tables in the database.
        
        Args:
            schema: Schema name (default: public)
            
        Returns:
            List of table info
        """
        sql = """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name
        """
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(sql, (schema,))
            rows = cursor.fetchall()
            
            tables = []
            for row in rows:
                tables.append({
                    "table_name": row[0],
                    "table_type": row[1],
                })
            
            cursor.close()
            return tables
        except Exception as e:
            logger.error(f"PostgreSQL list_tables error: {e}")
            return [{"error": str(e)}]
    
    def describe_table(self, table: str, schema: str = "public") -> Dict[str, Any]:
        """Get table schema/columns.
        
        Args:
            table: Table name
            schema: Schema name
            
        Returns:
            Table schema info
        """
        if not table:
            return {"error": "table name is required"}
        
        sql = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(sql, (schema, table))
            rows = cursor.fetchall()
            
            if not rows:
                return {"error": f"Table '{table}' not found"}
            
            columns = []
            for row in rows:
                columns.append({
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "default": row[3],
                })
            
            cursor.close()
            return {
                "table": table,
                "schema": schema,
                "columns": columns,
            }
        except Exception as e:
            logger.error(f"PostgreSQL describe_table error: {e}")
            return {"error": str(e)}
    
    def close(self):
        """Close database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()


def query_postgres(sql: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Execute PostgreSQL query."""
    return PostgresTool().query(sql=sql, limit=limit)


def list_postgres_tables() -> List[Dict[str, Any]]:
    """List PostgreSQL tables."""
    return PostgresTool().list_tables()
