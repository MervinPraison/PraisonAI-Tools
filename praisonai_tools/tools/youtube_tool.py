"""YouTube Tool for PraisonAI Agents.

Search YouTube videos, get video info, and retrieve transcripts.

Usage:
    from praisonai_tools import YouTubeTool
    
    yt = YouTubeTool()  # Uses YOUTUBE_API_KEY env var
    
    # Search videos
    results = yt.search("python tutorial")
    
    # Get video info
    info = yt.get_video("dQw4w9WgXcQ")
    
    # Get transcript
    transcript = yt.get_transcript("dQw4w9WgXcQ")

Environment Variables:
    YOUTUBE_API_KEY: YouTube Data API v3 key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class YouTubeTool(BaseTool):
    """Tool for interacting with YouTube."""
    
    name = "youtube"
    description = "Search YouTube videos, get video information, and retrieve transcripts."
    
    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        """Initialize YouTubeTool.
        
        Args:
            api_key: YouTube Data API key (or use YOUTUBE_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.api_base = "https://www.googleapis.com/youtube/v3"
        super().__init__()
    
    def _request(self, endpoint: str, params: Dict) -> Dict:
        """Make YouTube API request."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        if not self.api_key:
            return {"error": "YOUTUBE_API_KEY not configured"}
        
        try:
            params["key"] = self.api_key
            url = f"{self.api_base}/{endpoint}"
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"YouTube API error: {e}")
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        video_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        """Execute YouTube action.
        
        Args:
            action: "search", "video", "channel", "transcript"
            query: Search query
            video_id: YouTube video ID
            channel_id: YouTube channel ID
            limit: Max results
        """
        action = action.lower()
        
        if action == "search":
            return self.search(query=query, limit=limit, **kwargs)
        elif action in ("video", "get_video"):
            return self.get_video(video_id=video_id)
        elif action in ("channel", "get_channel"):
            return self.get_channel(channel_id=channel_id)
        elif action == "transcript":
            return self.get_transcript(video_id=video_id)
        elif action == "comments":
            return self.get_comments(video_id=video_id, limit=limit)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(
        self,
        query: str,
        limit: int = 10,
        video_type: str = "video",
        order: str = "relevance",
    ) -> List[Dict[str, Any]]:
        """Search YouTube videos.
        
        Args:
            query: Search query
            limit: Max results (max 50)
            video_type: "video", "channel", "playlist"
            order: "relevance", "date", "viewCount", "rating"
            
        Returns:
            List of search results
        """
        if not query:
            return [{"error": "Query is required"}]
        
        params = {
            "part": "snippet",
            "q": query,
            "type": video_type,
            "maxResults": min(limit, 50),
            "order": order,
        }
        
        result = self._request("search", params)
        
        if "error" in result:
            return [result]
        
        items = []
        for item in result.get("items", []):
            snippet = item.get("snippet", {})
            item_id = item.get("id", {})
            
            items.append({
                "video_id": item_id.get("videoId"),
                "channel_id": item_id.get("channelId") or snippet.get("channelId"),
                "title": snippet.get("title"),
                "description": snippet.get("description", "")[:200],
                "channel_title": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url"),
                "url": f"https://youtube.com/watch?v={item_id.get('videoId')}" if item_id.get("videoId") else None,
            })
        
        return items
    
    def get_video(self, video_id: str) -> Dict[str, Any]:
        """Get video details.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Video information
        """
        if not video_id:
            return {"error": "Video ID is required"}
        
        # Extract video ID from URL if needed
        video_id = self._extract_video_id(video_id)
        
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": video_id,
        }
        
        result = self._request("videos", params)
        
        if "error" in result:
            return result
        
        items = result.get("items", [])
        if not items:
            return {"error": "Video not found"}
        
        video = items[0]
        snippet = video.get("snippet", {})
        stats = video.get("statistics", {})
        content = video.get("contentDetails", {})
        
        return {
            "video_id": video_id,
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "channel_id": snippet.get("channelId"),
            "channel_title": snippet.get("channelTitle"),
            "published_at": snippet.get("publishedAt"),
            "duration": content.get("duration"),
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0)),
            "tags": snippet.get("tags", []),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "url": f"https://youtube.com/watch?v={video_id}",
        }
    
    def get_channel(self, channel_id: str) -> Dict[str, Any]:
        """Get channel details.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            Channel information
        """
        if not channel_id:
            return {"error": "Channel ID is required"}
        
        params = {
            "part": "snippet,statistics",
            "id": channel_id,
        }
        
        result = self._request("channels", params)
        
        if "error" in result:
            return result
        
        items = result.get("items", [])
        if not items:
            return {"error": "Channel not found"}
        
        channel = items[0]
        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})
        
        return {
            "channel_id": channel_id,
            "title": snippet.get("title"),
            "description": snippet.get("description", "")[:500],
            "custom_url": snippet.get("customUrl"),
            "published_at": snippet.get("publishedAt"),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "view_count": int(stats.get("viewCount", 0)),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "url": f"https://youtube.com/channel/{channel_id}",
        }
    
    def get_transcript(self, video_id: str, language: str = "en") -> Dict[str, Any]:
        """Get video transcript/captions.
        
        Args:
            video_id: YouTube video ID
            language: Language code (default: "en")
            
        Returns:
            Transcript text
        """
        if not video_id:
            return {"error": "Video ID is required"}
        
        video_id = self._extract_video_id(video_id)
        
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            return {"error": "youtube_transcript_api not installed. Install with: pip install youtube-transcript-api"}
        
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get the requested language
            try:
                transcript = transcript_list.find_transcript([language])
            except Exception:
                # Fall back to any available transcript
                transcript = transcript_list.find_generated_transcript([language, "en"])
            
            transcript_data = transcript.fetch()
            
            # Combine transcript segments
            full_text = " ".join([entry["text"] for entry in transcript_data])
            
            return {
                "video_id": video_id,
                "language": transcript.language_code,
                "is_generated": transcript.is_generated,
                "transcript": full_text,
                "segments": transcript_data[:50],  # First 50 segments
            }
        except Exception as e:
            logger.error(f"Transcript error: {e}")
            return {"error": f"Could not get transcript: {str(e)}"}
    
    def get_comments(self, video_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get video comments.
        
        Args:
            video_id: YouTube video ID
            limit: Max comments to return
            
        Returns:
            List of comments
        """
        if not video_id:
            return [{"error": "Video ID is required"}]
        
        video_id = self._extract_video_id(video_id)
        
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(limit, 100),
            "order": "relevance",
        }
        
        result = self._request("commentThreads", params)
        
        if "error" in result:
            return [result]
        
        comments = []
        for item in result.get("items", []):
            snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            comments.append({
                "author": snippet.get("authorDisplayName"),
                "text": snippet.get("textDisplay"),
                "like_count": snippet.get("likeCount", 0),
                "published_at": snippet.get("publishedAt"),
            })
        
        return comments
    
    @staticmethod
    def _extract_video_id(url_or_id: str) -> str:
        """Extract video ID from URL or return as-is if already an ID."""
        import re
        
        # Already an ID
        if len(url_or_id) == 11 and not url_or_id.startswith("http"):
            return url_or_id
        
        # YouTube URL patterns
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)
        
        return url_or_id


def search_youtube(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search YouTube videos."""
    return YouTubeTool().search(query=query, limit=limit)


def get_youtube_video(video_id: str) -> Dict[str, Any]:
    """Get YouTube video details."""
    return YouTubeTool().get_video(video_id=video_id)


def get_youtube_transcript(video_id: str) -> Dict[str, Any]:
    """Get YouTube video transcript."""
    return YouTubeTool().get_transcript(video_id=video_id)
