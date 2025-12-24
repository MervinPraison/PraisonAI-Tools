"""X (Twitter) Tool for PraisonAI Agents.

Post and search on X (Twitter).

Usage:
    from praisonai_tools import XTool
    
    x = XTool()
    x.post("Hello world!")

Environment Variables:
    X_API_KEY: X API key
    X_API_SECRET: X API secret
    X_ACCESS_TOKEN: X access token
    X_ACCESS_SECRET: X access token secret
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class XTool(BaseTool):
    """Tool for X (Twitter) operations."""
    
    name = "x"
    description = "Post and search on X (Twitter)."
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_secret: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("X_API_KEY")
        self.api_secret = api_secret or os.getenv("X_API_SECRET")
        self.access_token = access_token or os.getenv("X_ACCESS_TOKEN")
        self.access_secret = access_secret or os.getenv("X_ACCESS_SECRET")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                import tweepy
            except ImportError:
                raise ImportError("tweepy not installed. Install with: pip install tweepy")
            
            if not all([self.api_key, self.api_secret, self.access_token, self.access_secret]):
                raise ValueError("X API credentials required")
            
            self._client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_secret,
            )
        return self._client
    
    def run(
        self,
        action: str = "post",
        text: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "post":
            return self.post(text=text)
        elif action == "search":
            return self.search(query=query, **kwargs)
        elif action == "get_user":
            return self.get_user(username=kwargs.get("username"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def post(self, text: str) -> Dict[str, Any]:
        """Post a tweet."""
        if not text:
            return {"error": "text is required"}
        
        try:
            response = self.client.create_tweet(text=text)
            return {"success": True, "id": response.data["id"]}
        except Exception as e:
            logger.error(f"X post error: {e}")
            return {"error": str(e)}
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search tweets."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            response = self.client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),
                tweet_fields=["created_at", "author_id", "public_metrics"],
            )
            
            tweets = []
            for tweet in response.data or []:
                tweets.append({
                    "id": tweet.id,
                    "text": tweet.text,
                    "created_at": str(tweet.created_at) if tweet.created_at else None,
                    "author_id": tweet.author_id,
                    "metrics": tweet.public_metrics,
                })
            return tweets
        except Exception as e:
            logger.error(f"X search error: {e}")
            return [{"error": str(e)}]
    
    def get_user(self, username: str) -> Dict[str, Any]:
        """Get user info."""
        if not username:
            return {"error": "username is required"}
        
        try:
            response = self.client.get_user(
                username=username,
                user_fields=["description", "public_metrics", "created_at"],
            )
            user = response.data
            return {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "description": user.description,
                "metrics": user.public_metrics,
            }
        except Exception as e:
            logger.error(f"X get_user error: {e}")
            return {"error": str(e)}


def post_to_x(text: str) -> Dict[str, Any]:
    """Post to X."""
    return XTool().post(text=text)
