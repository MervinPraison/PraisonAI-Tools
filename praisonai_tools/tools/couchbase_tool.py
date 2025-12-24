"""Couchbase Tool for PraisonAI Agents.

Couchbase database operations.

Usage:
    from praisonai_tools import CouchbaseTool
    
    cb = CouchbaseTool()
    doc = cb.get(bucket="default", key="user:123")

Environment Variables:
    COUCHBASE_CONNECTION_STRING: Connection string
    COUCHBASE_USERNAME: Username
    COUCHBASE_PASSWORD: Password
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class CouchbaseTool(BaseTool):
    """Tool for Couchbase operations."""
    
    name = "couchbase"
    description = "Couchbase database operations."
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.connection_string = connection_string or os.getenv("COUCHBASE_CONNECTION_STRING", "couchbase://localhost")
        self.username = username or os.getenv("COUCHBASE_USERNAME")
        self.password = password or os.getenv("COUCHBASE_PASSWORD")
        self._cluster = None
        super().__init__()
    
    @property
    def cluster(self):
        if self._cluster is None:
            try:
                from couchbase.cluster import Cluster
                from couchbase.options import ClusterOptions
                from couchbase.auth import PasswordAuthenticator
            except ImportError:
                raise ImportError("couchbase not installed")
            auth = PasswordAuthenticator(self.username, self.password)
            self._cluster = Cluster(self.connection_string, ClusterOptions(auth))
        return self._cluster
    
    def run(
        self,
        action: str = "get",
        bucket: Optional[str] = None,
        key: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "get":
            return self.get(bucket=bucket, key=key)
        elif action == "upsert":
            return self.upsert(bucket=bucket, key=key, value=kwargs.get("value"))
        elif action == "query":
            return self.query(sql=kwargs.get("sql"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def get(self, bucket: str, key: str) -> Dict[str, Any]:
        """Get document by key."""
        if not bucket or not key:
            return {"error": "bucket and key are required"}
        try:
            b = self.cluster.bucket(bucket)
            coll = b.default_collection()
            result = coll.get(key)
            return {"key": key, "value": result.content_as[dict]}
        except Exception as e:
            logger.error(f"Couchbase get error: {e}")
            return {"error": str(e)}
    
    def upsert(self, bucket: str, key: str, value: Dict) -> Dict[str, Any]:
        """Upsert document."""
        if not bucket or not key or not value:
            return {"error": "bucket, key, and value are required"}
        try:
            b = self.cluster.bucket(bucket)
            coll = b.default_collection()
            coll.upsert(key, value)
            return {"success": True}
        except Exception as e:
            logger.error(f"Couchbase upsert error: {e}")
            return {"error": str(e)}
    
    def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute N1QL query."""
        if not sql:
            return [{"error": "sql is required"}]
        try:
            result = self.cluster.query(sql)
            return [row for row in result]
        except Exception as e:
            logger.error(f"Couchbase query error: {e}")
            return [{"error": str(e)}]


def couchbase_get(bucket: str, key: str) -> Dict[str, Any]:
    """Get from Couchbase."""
    return CouchbaseTool().get(bucket=bucket, key=key)
