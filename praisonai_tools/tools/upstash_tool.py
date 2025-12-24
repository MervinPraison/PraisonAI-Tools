"""Upstash Tool for PraisonAI Agents.

Upstash Redis and Vector operations.

Usage:
    from praisonai_tools import UpstashTool
    
    upstash = UpstashTool()
    upstash.set("key", "value")

Environment Variables:
    UPSTASH_REDIS_REST_URL: Upstash Redis REST URL
    UPSTASH_REDIS_REST_TOKEN: Upstash Redis REST token
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class UpstashTool(BaseTool):
    """Tool for Upstash Redis operations."""
    
    name = "upstash"
    description = "Upstash Redis and Vector operations."
    
    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
    ):
        self.url = url or os.getenv("UPSTASH_REDIS_REST_URL")
        self.token = token or os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self._redis = None
        super().__init__()
    
    @property
    def redis(self):
        if self._redis is None:
            try:
                from upstash_redis import Redis
            except ImportError:
                raise ImportError("upstash-redis not installed. Install with: pip install upstash-redis")
            if not self.url or not self.token:
                raise ValueError("UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN required")
            self._redis = Redis(url=self.url, token=self.token)
        return self._redis
    
    def run(
        self,
        action: str = "get",
        key: Optional[str] = None,
        value: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        action = action.lower().replace("-", "_")
        
        if action == "get":
            return self.get(key=key)
        elif action == "set":
            return self.set(key=key, value=value, **kwargs)
        elif action == "delete":
            return self.delete(key=key)
        elif action == "keys":
            return self.keys(pattern=kwargs.get("pattern", "*"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def get(self, key: str) -> Dict[str, Any]:
        """Get value by key."""
        if not key:
            return {"error": "key is required"}
        try:
            value = self.redis.get(key)
            return {"key": key, "value": value}
        except Exception as e:
            logger.error(f"Upstash get error: {e}")
            return {"error": str(e)}
    
    def set(self, key: str, value: str, ex: int = None) -> Dict[str, Any]:
        """Set key-value pair."""
        if not key or value is None:
            return {"error": "key and value are required"}
        try:
            if ex:
                self.redis.set(key, value, ex=ex)
            else:
                self.redis.set(key, value)
            return {"success": True}
        except Exception as e:
            logger.error(f"Upstash set error: {e}")
            return {"error": str(e)}
    
    def delete(self, key: str) -> Dict[str, Any]:
        """Delete key."""
        if not key:
            return {"error": "key is required"}
        try:
            self.redis.delete(key)
            return {"success": True}
        except Exception as e:
            logger.error(f"Upstash delete error: {e}")
            return {"error": str(e)}
    
    def keys(self, pattern: str = "*") -> List[str]:
        """List keys matching pattern."""
        try:
            return self.redis.keys(pattern)
        except Exception as e:
            logger.error(f"Upstash keys error: {e}")
            return [{"error": str(e)}]


def upstash_get(key: str) -> Dict[str, Any]:
    """Get from Upstash."""
    return UpstashTool().get(key=key)
