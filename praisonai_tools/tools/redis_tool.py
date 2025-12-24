"""Redis Tool for PraisonAI Agents.

Interact with Redis key-value store.

Usage:
    from praisonai_tools import RedisTool
    
    redis = RedisTool()
    redis.set(key="mykey", value="myvalue")
    value = redis.get(key="mykey")

Environment Variables:
    REDIS_URL: Redis connection URL (default: redis://localhost:6379)
    REDIS_HOST: Redis host
    REDIS_PORT: Redis port
    REDIS_PASSWORD: Redis password
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class RedisTool(BaseTool):
    """Tool for interacting with Redis."""
    
    name = "redis"
    description = "Get, set, and manage Redis keys."
    
    def __init__(
        self,
        url: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        db: int = 0,
    ):
        self.url = url or os.getenv("REDIS_URL")
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port or int(os.getenv("REDIS_PORT", "6379"))
        self.password = password or os.getenv("REDIS_PASSWORD")
        self.db = db
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                import redis
            except ImportError:
                raise ImportError("redis not installed. Install with: pip install redis")
            
            if self.url:
                self._client = redis.from_url(self.url)
            else:
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    db=self.db,
                    decode_responses=True,
                )
        return self._client
    
    def run(
        self,
        action: str = "get",
        key: Optional[str] = None,
        value: Optional[str] = None,
        pattern: str = "*",
        **kwargs
    ) -> Union[str, Dict[str, Any], List[str]]:
        action = action.lower().replace("-", "_")
        
        if action == "get":
            return self.get(key=key)
        elif action == "set":
            return self.set(key=key, value=value, **kwargs)
        elif action == "delete":
            return self.delete(key=key)
        elif action == "keys":
            return self.keys(pattern=pattern)
        elif action == "exists":
            return self.exists(key=key)
        elif action == "expire":
            return self.expire(key=key, seconds=kwargs.get("seconds", 60))
        elif action == "ttl":
            return self.ttl(key=key)
        elif action == "hget":
            return self.hget(key=key, field=kwargs.get("field"))
        elif action == "hset":
            return self.hset(key=key, field=kwargs.get("field"), value=value)
        elif action == "hgetall":
            return self.hgetall(key=key)
        elif action == "lpush":
            return self.lpush(key=key, value=value)
        elif action == "lrange":
            return self.lrange(key=key, start=kwargs.get("start", 0), end=kwargs.get("end", -1))
        elif action == "info":
            return self.info()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def get(self, key: str) -> Dict[str, Any]:
        """Get value by key."""
        if not key:
            return {"error": "key is required"}
        try:
            value = self.client.get(key)
            return {"key": key, "value": value}
        except Exception as e:
            return {"error": str(e)}
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> Dict[str, Any]:
        """Set key-value pair."""
        if not key:
            return {"error": "key is required"}
        if value is None:
            return {"error": "value is required"}
        try:
            self.client.set(key, value, ex=ex)
            return {"success": True, "key": key}
        except Exception as e:
            return {"error": str(e)}
    
    def delete(self, key: str) -> Dict[str, Any]:
        """Delete key."""
        if not key:
            return {"error": "key is required"}
        try:
            deleted = self.client.delete(key)
            return {"success": True, "deleted": deleted}
        except Exception as e:
            return {"error": str(e)}
    
    def keys(self, pattern: str = "*") -> List[str]:
        """List keys matching pattern."""
        try:
            return self.client.keys(pattern)
        except Exception as e:
            return [f"error: {e}"]
    
    def exists(self, key: str) -> Dict[str, Any]:
        """Check if key exists."""
        if not key:
            return {"error": "key is required"}
        try:
            exists = self.client.exists(key)
            return {"key": key, "exists": bool(exists)}
        except Exception as e:
            return {"error": str(e)}
    
    def expire(self, key: str, seconds: int) -> Dict[str, Any]:
        """Set key expiration."""
        if not key:
            return {"error": "key is required"}
        try:
            result = self.client.expire(key, seconds)
            return {"success": result, "key": key, "expires_in": seconds}
        except Exception as e:
            return {"error": str(e)}
    
    def ttl(self, key: str) -> Dict[str, Any]:
        """Get time to live."""
        if not key:
            return {"error": "key is required"}
        try:
            ttl = self.client.ttl(key)
            return {"key": key, "ttl": ttl}
        except Exception as e:
            return {"error": str(e)}
    
    def hget(self, key: str, field: str) -> Dict[str, Any]:
        """Get hash field."""
        if not key or not field:
            return {"error": "key and field are required"}
        try:
            value = self.client.hget(key, field)
            return {"key": key, "field": field, "value": value}
        except Exception as e:
            return {"error": str(e)}
    
    def hset(self, key: str, field: str, value: str) -> Dict[str, Any]:
        """Set hash field."""
        if not key or not field:
            return {"error": "key and field are required"}
        try:
            self.client.hset(key, field, value)
            return {"success": True, "key": key, "field": field}
        except Exception as e:
            return {"error": str(e)}
    
    def hgetall(self, key: str) -> Dict[str, Any]:
        """Get all hash fields."""
        if not key:
            return {"error": "key is required"}
        try:
            data = self.client.hgetall(key)
            return {"key": key, "data": data}
        except Exception as e:
            return {"error": str(e)}
    
    def lpush(self, key: str, value: str) -> Dict[str, Any]:
        """Push to list."""
        if not key:
            return {"error": "key is required"}
        try:
            length = self.client.lpush(key, value)
            return {"success": True, "key": key, "length": length}
        except Exception as e:
            return {"error": str(e)}
    
    def lrange(self, key: str, start: int = 0, end: int = -1) -> Dict[str, Any]:
        """Get list range."""
        if not key:
            return {"error": "key is required"}
        try:
            values = self.client.lrange(key, start, end)
            return {"key": key, "values": values}
        except Exception as e:
            return {"error": str(e)}
    
    def info(self) -> Dict[str, Any]:
        """Get Redis info."""
        try:
            info = self.client.info()
            return {
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "total_keys": sum(info.get(f"db{i}", {}).get("keys", 0) for i in range(16)),
            }
        except Exception as e:
            return {"error": str(e)}


def redis_get(key: str) -> Dict[str, Any]:
    """Get Redis key."""
    return RedisTool().get(key=key)


def redis_set(key: str, value: str) -> Dict[str, Any]:
    """Set Redis key."""
    return RedisTool().set(key=key, value=value)
