"""Cassandra Tool for PraisonAI Agents.

Apache Cassandra database operations.

Usage:
    from praisonai_tools import CassandraTool
    
    cassandra = CassandraTool()
    results = cassandra.query("SELECT * FROM users")

Environment Variables:
    CASSANDRA_HOST: Cassandra host
    CASSANDRA_PORT: Cassandra port
    CASSANDRA_KEYSPACE: Keyspace name
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class CassandraTool(BaseTool):
    """Tool for Cassandra operations."""
    
    name = "cassandra"
    description = "Apache Cassandra database operations."
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        keyspace: Optional[str] = None,
    ):
        self.host = host or os.getenv("CASSANDRA_HOST", "localhost")
        self.port = port or int(os.getenv("CASSANDRA_PORT", "9042"))
        self.keyspace = keyspace or os.getenv("CASSANDRA_KEYSPACE")
        self._session = None
        super().__init__()
    
    @property
    def session(self):
        if self._session is None:
            try:
                from cassandra.cluster import Cluster
            except ImportError:
                raise ImportError("cassandra-driver not installed")
            cluster = Cluster([self.host], port=self.port)
            self._session = cluster.connect(self.keyspace)
        return self._session
    
    def run(
        self,
        action: str = "query",
        cql: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "query":
            return self.query(cql=cql)
        elif action == "execute":
            return self.execute(cql=cql)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def query(self, cql: str) -> List[Dict[str, Any]]:
        """Execute CQL query."""
        if not cql:
            return [{"error": "cql is required"}]
        
        try:
            rows = self.session.execute(cql)
            return [dict(row._asdict()) for row in rows]
        except Exception as e:
            logger.error(f"Cassandra query error: {e}")
            return [{"error": str(e)}]
    
    def execute(self, cql: str) -> Dict[str, Any]:
        """Execute CQL statement."""
        if not cql:
            return {"error": "cql is required"}
        
        try:
            self.session.execute(cql)
            return {"success": True}
        except Exception as e:
            logger.error(f"Cassandra execute error: {e}")
            return {"error": str(e)}


def cassandra_query(cql: str) -> List[Dict[str, Any]]:
    """Query Cassandra."""
    return CassandraTool().query(cql=cql)
