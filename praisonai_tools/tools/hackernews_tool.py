"""Hacker News Tool for PraisonAI Agents.

Get stories and comments from Hacker News.

Usage:
    from praisonai_tools import HackerNewsTool
    
    hn = HackerNewsTool()
    stories = hn.get_top_stories()
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class HackerNewsTool(BaseTool):
    """Tool for Hacker News."""
    
    name = "hackernews"
    description = "Get top stories, new stories, and comments from Hacker News."
    
    def __init__(self):
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        super().__init__()
    
    def run(
        self,
        action: str = "top_stories",
        story_id: Optional[int] = None,
        limit: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "top_stories":
            return self.get_top_stories(limit=limit)
        elif action == "new_stories":
            return self.get_new_stories(limit=limit)
        elif action == "best_stories":
            return self.get_best_stories(limit=limit)
        elif action == "get_story":
            return self.get_story(story_id=story_id)
        elif action == "get_comments":
            return self.get_comments(story_id=story_id, limit=limit)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def _fetch(self, endpoint: str) -> Any:
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            resp = requests.get(f"{self.base_url}/{endpoint}.json", timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_top_stories(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top stories."""
        ids = self._fetch("topstories")
        if isinstance(ids, dict) and "error" in ids:
            return [ids]
        
        stories = []
        for story_id in ids[:limit]:
            story = self._fetch(f"item/{story_id}")
            if story and not isinstance(story, dict) or "error" not in story:
                stories.append({
                    "id": story.get("id"),
                    "title": story.get("title"),
                    "url": story.get("url"),
                    "score": story.get("score"),
                    "by": story.get("by"),
                    "descendants": story.get("descendants", 0),
                })
        return stories
    
    def get_new_stories(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get new stories."""
        ids = self._fetch("newstories")
        if isinstance(ids, dict) and "error" in ids:
            return [ids]
        
        stories = []
        for story_id in ids[:limit]:
            story = self._fetch(f"item/{story_id}")
            if story:
                stories.append({
                    "id": story.get("id"),
                    "title": story.get("title"),
                    "url": story.get("url"),
                    "score": story.get("score"),
                    "by": story.get("by"),
                })
        return stories
    
    def get_best_stories(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get best stories."""
        ids = self._fetch("beststories")
        if isinstance(ids, dict) and "error" in ids:
            return [ids]
        
        stories = []
        for story_id in ids[:limit]:
            story = self._fetch(f"item/{story_id}")
            if story:
                stories.append({
                    "id": story.get("id"),
                    "title": story.get("title"),
                    "url": story.get("url"),
                    "score": story.get("score"),
                    "by": story.get("by"),
                })
        return stories
    
    def get_story(self, story_id: int) -> Dict[str, Any]:
        """Get story details."""
        if not story_id:
            return {"error": "story_id is required"}
        
        story = self._fetch(f"item/{story_id}")
        if isinstance(story, dict) and "error" in story:
            return story
        
        return {
            "id": story.get("id"),
            "title": story.get("title"),
            "url": story.get("url"),
            "text": story.get("text"),
            "score": story.get("score"),
            "by": story.get("by"),
            "time": story.get("time"),
            "descendants": story.get("descendants", 0),
            "kids": story.get("kids", [])[:10],
        }
    
    def get_comments(self, story_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get story comments."""
        if not story_id:
            return [{"error": "story_id is required"}]
        
        story = self._fetch(f"item/{story_id}")
        if isinstance(story, dict) and "error" in story:
            return [story]
        
        comment_ids = story.get("kids", [])[:limit]
        comments = []
        
        for cid in comment_ids:
            comment = self._fetch(f"item/{cid}")
            if comment and comment.get("type") == "comment":
                comments.append({
                    "id": comment.get("id"),
                    "by": comment.get("by"),
                    "text": comment.get("text", "")[:500],
                    "time": comment.get("time"),
                })
        return comments


def get_hackernews_top(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top Hacker News stories."""
    return HackerNewsTool().get_top_stories(limit=limit)
