"""Threads Tool for PraisonAI Agents.

Post to Meta Threads using the official Threads API.

Usage:
    from praisonai_tools import ThreadsTool

    t = ThreadsTool()
    t.post_text("Hello from PraisonAI!")

Environment Variables:
    THREADS_ACCESS_TOKEN: Threads user access token
    THREADS_USER_ID: Threads user ID
"""

import os
import time
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v20.0"
GRAPH_API_BASE = f"https://graph.threads.net/{GRAPH_API_VERSION}"


class ThreadsTool(BaseTool):
    """Tool for Meta Threads API operations."""

    name = "threads"
    description = "Post content to Meta Threads."

    def __init__(
        self,
        access_token: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.access_token = access_token or os.getenv("THREADS_ACCESS_TOKEN")
        self.user_id = user_id or os.getenv("THREADS_USER_ID")
        super().__init__()

    def run(self, action: str = "post_text", **kwargs):
        action = action.lower().replace("-", "_")
        handler = getattr(self, action, None)
        if handler and callable(handler) and not action.startswith("_"):
            return handler(**kwargs)
        return {"error": f"Unknown action: {action}"}

    def post_text(self, text: str) -> Dict[str, Any]:
        """Post a text thread.

        Args:
            text: Thread text content (max 500 chars).
        """
        if not text:
            return {"error": "text is required"}
        if not self.access_token:
            return {"error": "THREADS_ACCESS_TOKEN required"}
        if not self.user_id:
            return {"error": "THREADS_USER_ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. pip install requests"}

        # Step 1: Create container
        resp = requests.post(
            f"{GRAPH_API_BASE}/{self.user_id}/threads",
            data={
                "media_type": "TEXT",
                "text": text,
                "access_token": self.access_token,
            },
        )
        if resp.status_code != 200:
            return {"error": f"Container creation failed: {resp.status_code}", "detail": resp.json()}

        container_id = resp.json().get("id")

        # Step 2: Wait briefly for processing
        time.sleep(5)

        # Step 3: Publish
        pub_resp = requests.post(
            f"{GRAPH_API_BASE}/{self.user_id}/threads_publish",
            data={"creation_id": container_id, "access_token": self.access_token},
        )
        if pub_resp.status_code == 200:
            return {"success": True, "thread_id": pub_resp.json().get("id")}
        return {"error": f"Publish failed: {pub_resp.status_code}", "detail": pub_resp.json()}

    def post_image(self, image_url: str, text: str = "") -> Dict[str, Any]:
        """Post an image thread.

        Args:
            image_url: Public URL of the image.
            text: Thread text caption.
        """
        if not image_url:
            return {"error": "image_url is required (must be public URL)"}
        if not self.access_token or not self.user_id:
            return {"error": "THREADS_ACCESS_TOKEN and THREADS_USER_ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        data = {
            "media_type": "IMAGE",
            "image_url": image_url,
            "access_token": self.access_token,
        }
        if text:
            data["text"] = text

        resp = requests.post(f"{GRAPH_API_BASE}/{self.user_id}/threads", data=data)
        if resp.status_code != 200:
            return {"error": f"Container failed: {resp.status_code}", "detail": resp.json()}

        container_id = resp.json().get("id")
        time.sleep(5)

        pub_resp = requests.post(
            f"{GRAPH_API_BASE}/{self.user_id}/threads_publish",
            data={"creation_id": container_id, "access_token": self.access_token},
        )
        if pub_resp.status_code == 200:
            return {"success": True, "thread_id": pub_resp.json().get("id")}
        return {"error": f"Publish failed: {pub_resp.status_code}", "detail": pub_resp.json()}

    def post_video(self, video_url: str, text: str = "") -> Dict[str, Any]:
        """Post a video thread.

        Args:
            video_url: Public URL of the video (MP4).
            text: Thread text caption.
        """
        if not video_url:
            return {"error": "video_url is required (must be public URL)"}
        if not self.access_token or not self.user_id:
            return {"error": "THREADS_ACCESS_TOKEN and THREADS_USER_ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        data = {
            "media_type": "VIDEO",
            "video_url": video_url,
            "access_token": self.access_token,
        }
        if text:
            data["text"] = text

        resp = requests.post(f"{GRAPH_API_BASE}/{self.user_id}/threads", data=data)
        if resp.status_code != 200:
            return {"error": f"Container failed: {resp.status_code}", "detail": resp.json()}

        container_id = resp.json().get("id")

        # Video needs more processing time
        for _ in range(30):
            time.sleep(10)
            status_resp = requests.get(
                f"{GRAPH_API_BASE}/{container_id}",
                params={"fields": "status", "access_token": self.access_token},
            )
            if status_resp.status_code == 200:
                status = status_resp.json().get("status")
                if status == "FINISHED":
                    break
                elif status == "ERROR":
                    return {"error": "Video processing failed", "detail": status_resp.json()}

        pub_resp = requests.post(
            f"{GRAPH_API_BASE}/{self.user_id}/threads_publish",
            data={"creation_id": container_id, "access_token": self.access_token},
        )
        if pub_resp.status_code == 200:
            return {"success": True, "thread_id": pub_resp.json().get("id")}
        return {"error": f"Publish failed: {pub_resp.status_code}", "detail": pub_resp.json()}

    def post_carousel(self, items: List[Dict[str, str]], text: str = "") -> Dict[str, Any]:
        """Post a carousel thread (multiple media items).

        Args:
            items: List of dicts with 'media_type' (IMAGE/VIDEO) and 'url'.
            text: Thread text caption.
        """
        if not items or len(items) < 2:
            return {"error": "At least 2 items required for carousel"}
        if len(items) > 20:
            return {"error": "Maximum 20 items per carousel"}
        if not self.access_token or not self.user_id:
            return {"error": "THREADS_ACCESS_TOKEN and THREADS_USER_ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        # Create child containers
        children_ids = []
        for item in items:
            media_type = item.get("media_type", "IMAGE").upper()
            url_key = "image_url" if media_type == "IMAGE" else "video_url"
            data = {
                "media_type": media_type,
                url_key: item.get("url", ""),
                "is_carousel_item": "true",
                "access_token": self.access_token,
            }
            resp = requests.post(f"{GRAPH_API_BASE}/{self.user_id}/threads", data=data)
            if resp.status_code != 200:
                return {"error": f"Carousel item failed: {resp.status_code}", "detail": resp.json()}
            children_ids.append(resp.json().get("id"))

        time.sleep(10)

        # Create carousel container
        data = {
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "access_token": self.access_token,
        }
        if text:
            data["text"] = text

        resp = requests.post(f"{GRAPH_API_BASE}/{self.user_id}/threads", data=data)
        if resp.status_code != 200:
            return {"error": f"Carousel creation failed: {resp.status_code}", "detail": resp.json()}

        container_id = resp.json().get("id")
        time.sleep(5)

        pub_resp = requests.post(
            f"{GRAPH_API_BASE}/{self.user_id}/threads_publish",
            data={"creation_id": container_id, "access_token": self.access_token},
        )
        if pub_resp.status_code == 200:
            return {"success": True, "thread_id": pub_resp.json().get("id")}
        return {"error": f"Publish failed: {pub_resp.status_code}", "detail": pub_resp.json()}

    def get_threads(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent threads.

        Args:
            limit: Number of threads (max 100).
        """
        if not self.access_token or not self.user_id:
            return {"error": "Credentials required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        resp = requests.get(
            f"{GRAPH_API_BASE}/{self.user_id}/threads",
            params={
                "fields": "id,text,media_type,timestamp,permalink",
                "limit": min(limit, 100),
                "access_token": self.access_token,
            },
        )
        if resp.status_code == 200:
            return {"success": True, "threads": resp.json().get("data", [])}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def get_profile(self) -> Dict[str, Any]:
        """Get Threads user profile."""
        if not self.access_token or not self.user_id:
            return {"error": "Credentials required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        resp = requests.get(
            f"{GRAPH_API_BASE}/{self.user_id}",
            params={
                "fields": "id,username,threads_profile_picture_url,threads_biography",
                "access_token": self.access_token,
            },
        )
        if resp.status_code == 200:
            return {"success": True, "profile": resp.json()}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}


# Standalone functions
def threads_post_text(
    text: str,
    access_token: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Post a text thread on Threads.

    Args:
        text: Thread text content (max 500 chars).
        access_token: Threads token (or set THREADS_ACCESS_TOKEN env var).
        user_id: Threads user ID (or set THREADS_USER_ID env var).
    """
    return ThreadsTool(access_token=access_token, user_id=user_id).post_text(text=text)


def threads_post_image(
    image_url: str,
    text: str = "",
    access_token: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Post an image thread on Threads.

    Args:
        image_url: Public URL of the image.
        text: Thread caption.
        access_token: Threads token.
        user_id: Threads user ID.
    """
    return ThreadsTool(access_token=access_token, user_id=user_id).post_image(
        image_url=image_url, text=text
    )


def threads_post_video(
    video_url: str,
    text: str = "",
    access_token: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Post a video thread on Threads.

    Args:
        video_url: Public URL of the video.
        text: Thread caption.
        access_token: Threads token.
        user_id: Threads user ID.
    """
    return ThreadsTool(access_token=access_token, user_id=user_id).post_video(
        video_url=video_url, text=text
    )


def threads_get_threads(
    limit: int = 10,
    access_token: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get recent threads.

    Args:
        limit: Number of threads.
        access_token: Threads token.
        user_id: Threads user ID.
    """
    return ThreadsTool(access_token=access_token, user_id=user_id).get_threads(limit=limit)


def threads_get_profile(
    access_token: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get Threads user profile.

    Args:
        access_token: Threads token.
        user_id: Threads user ID.
    """
    return ThreadsTool(access_token=access_token, user_id=user_id).get_profile()
