"""MySQL Tool for PraisonAI Agents.

Execute queries and interact with MySQL databases.

Usage:
    from praisonai_tools import MySQLTool
    
    mysql = MySQLTool(host="localhost", database="mydb", user="root", password="pass")
    results = mysql.query("SELECT * FROM users LIMIT 10")

Environment Variables:
    MYSQL_HOST: Database host
    MYSQL_PORT: Database port (default: 3306)
    MYSQL_DATABASE: Database name
    MYSQL_USER: Username
    MYSQL_PASSWORD: Password
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class MySQLTool(BaseTool):
    """Tool for interacting with MySQL databases."""
    
    name = "mysql"
    description = "Execute SQL queries on MySQL databases."
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host or os.getenv("MYSQL_HOST", "localhost")
        self.port = port or int(os.getenv("MYSQL_PORT", "3306"))
        self.database = database or os.getenv("MYSQL_DATABASE")
        self.user = user or os.getenv("MYSQL_USER")
        self.password = password or os.getenv("MYSQL_PASSWORD")
        self._conn = None
        super().__init__()
    
    def _get_connection(self):
        """Get database connection."""
        try:
            import mysql.connector
        except ImportError:
            raise ImportError("mysql-connector-python not installed. Install with: pip install mysql-connector-python")
        
        if self._conn is None or not self._conn.is_connected():
            if not all([self.host, self.database, self.user]):
                raise ValueError("Database connection parameters required")
            self._conn = mysql.connector.connect(
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
            return [{"error": "Only SELECT queries allowed. Use execute() for other statements."}]
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            if "LIMIT" not in sql_upper:
                sql = f"{sql.rstrip(';')} LIMIT {limit}"
            
            cursor.execute(sql)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"MySQL query error: {e}")
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
            logger.error(f"MySQL execute error: {e}")
            if self._conn:
                self._conn.rollback()
            return {"error": str(e)}
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """List all tables."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SHOW TABLES")
            rows = cursor.fetchall()
            cursor.close()
            
            tables = []
            for row in rows:
                table_name = list(row.values())[0]
                tables.append({"table_name": table_name})
            return tables
        except Exception as e:
            logger.error(f"MySQL list_tables error: {e}")
            return [{"error": str(e)}]
    
    def describe_table(self, table: str) -> Dict[str, Any]:
        """Get table schema."""
        if not table:
            return {"error": "table name is required"}
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"DESCRIBE {table}")
            rows = cursor.fetchall()
            cursor.close()
            
            if not rows:
                return {"error": f"Table '{table}' not found"}
            
            columns = []
            for row in rows:
                columns.append({
                    "name": row.get("Field"),
                    "type": row.get("Type"),
                    "nullable": row.get("Null") == "YES",
                    "key": row.get("Key"),
                    "default": row.get("Default"),
                })
            
            return {"table": table, "columns": columns}
        except Exception as e:
            logger.error(f"MySQL describe_table error: {e}")
            return {"error": str(e)}
    
    def close(self):
        if self._conn and self._conn.is_connected():
            self._conn.close()
            self._conn = None


def query_mysql(sql: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Execute MySQL query."""
    return MySQLTool().query(sql=sql, limit=limit)
