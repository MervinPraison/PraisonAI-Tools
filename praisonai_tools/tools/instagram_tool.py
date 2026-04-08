"""Instagram Tool for PraisonAI Agents.

Post to Instagram using the official Graph API (Business/Creator accounts).

Usage:
    from praisonai_tools import InstagramTool

    ig = InstagramTool()
    ig.post_image(image_url="https://example.com/photo.jpg", caption="Hello!")

Environment Variables:
    INSTAGRAM_ACCESS_TOKEN: Meta Graph API access token
    INSTAGRAM_BUSINESS_ACCOUNT_ID: Instagram Business/Creator account ID
"""

import os
import time
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v20.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class InstagramTool(BaseTool):
    """Tool for Instagram Graph API operations."""

    name = "instagram"
    description = "Post content to Instagram (Business/Creator accounts)."

    def __init__(
        self,
        access_token: Optional[str] = None,
        account_id: Optional[str] = None,
    ):
        self.access_token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.account_id = account_id or os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        super().__init__()

    def run(self, action: str = "post_image", **kwargs):
        action = action.lower().replace("-", "_")
        handler = getattr(self, action, None)
        if handler and callable(handler) and not action.startswith("_"):
            return handler(**kwargs)
        return {"error": f"Unknown action: {action}"}

    def post_image(
        self,
        image_url: str,
        caption: str = "",
        location_id: str = "",
        user_tags: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Post a single image to Instagram.

        Args:
            image_url: Public URL of the image (must be accessible by Meta servers).
            caption: Post caption (max 2200 chars, 30 hashtags).
            location_id: Facebook Place ID for location tag.
            user_tags: List of user tags [{username, x, y}].
        """
        if not image_url:
            return {"error": "image_url is required (must be a public URL)"}
        if not self.access_token:
            return {"error": "INSTAGRAM_ACCESS_TOKEN required"}
        if not self.account_id:
            return {"error": "INSTAGRAM_BUSINESS_ACCOUNT_ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. pip install requests"}

        # Step 1: Create media container
        container_data = {
            "image_url": image_url,
            "access_token": self.access_token,
        }
        if caption:
            container_data["caption"] = caption
        if location_id:
            container_data["location_id"] = location_id
        if user_tags:
            import json
            container_data["user_tags"] = json.dumps(user_tags)

        resp = requests.post(
            f"{GRAPH_API_BASE}/{self.account_id}/media",
            data=container_data,
        )
        if resp.status_code != 200:
            return {"error": f"Container creation failed: {resp.status_code}", "detail": resp.json()}

        container_id = resp.json().get("id")

        # Step 2: Wait for container to be ready (optional brief pause)
        time.sleep(3)

        # Step 3: Publish the container
        pub_resp = requests.post(
            f"{GRAPH_API_BASE}/{self.account_id}/media_publish",
            data={"creation_id": container_id, "access_token": self.access_token},
        )
        if pub_resp.status_code == 200:
            return {"success": True, "media_id": pub_resp.json().get("id")}
        return {"error": f"Publish failed: {pub_resp.status_code}", "detail": pub_resp.json()}

    def post_carousel(
        self,
        image_urls: List[str],
        caption: str = "",
    ) -> Dict[str, Any]:
        """Post a carousel (multiple images) to Instagram.

        Args:
            image_urls: List of public image URLs (2-10 images).
            caption: Post caption.
        """
        if not image_urls or len(image_urls) < 2:
            return {"error": "At least 2 image_urls required for carousel"}
        if len(image_urls) > 10:
            return {"error": "Maximum 10 images per carousel"}
        if not self.access_token:
            return {"error": "INSTAGRAM_ACCESS_TOKEN required"}
        if not self.account_id:
            return {"error": "INSTAGRAM_BUSINESS_ACCOUNT_ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        # Step 1: Create individual media containers for each image
        children_ids = []
        for url in image_urls:
            resp = requests.post(
                f"{GRAPH_API_BASE}/{self.account_id}/media",
                data={
                    "image_url": url,
                    "is_carousel_item": "true",
                    "access_token": self.access_token,
                },
            )
            if resp.status_code != 200:
                return {"error": f"Failed creating carousel item: {resp.status_code}", "detail": resp.json()}
            children_ids.append(resp.json().get("id"))

        time.sleep(5)

        # Step 2: Create carousel container
        carousel_data = {
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "access_token": self.access_token,
        }
        if caption:
            carousel_data["caption"] = caption

        resp = requests.post(
            f"{GRAPH_API_BASE}/{self.account_id}/media",
            data=carousel_data,
        )
        if resp.status_code != 200:
            return {"error": f"Carousel creation failed: {resp.status_code}", "detail": resp.json()}

        carousel_id = resp.json().get("id")
        time.sleep(5)

        # Step 3: Publish
        pub_resp = requests.post(
            f"{GRAPH_API_BASE}/{self.account_id}/media_publish",
            data={"creation_id": carousel_id, "access_token": self.access_token},
        )
        if pub_resp.status_code == 200:
            return {"success": True, "media_id": pub_resp.json().get("id")}
        return {"error": f"Publish failed: {pub_resp.status_code}", "detail": pub_resp.json()}

    def post_reel(
        self,
        video_url: str,
        caption: str = "",
        share_to_feed: bool = True,
    ) -> Dict[str, Any]:
        """Post a Reel (short video) to Instagram.

        Args:
            video_url: Public URL of the video (MP4, max 90 seconds).
            caption: Reel caption.
            share_to_feed: Also share to main feed.
        """
        if not video_url:
            return {"error": "video_url is required (must be a public URL)"}
        if not self.access_token:
            return {"error": "INSTAGRAM_ACCESS_TOKEN required"}
        if not self.account_id:
            return {"error": "INSTAGRAM_BUSINESS_ACCOUNT_ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        # Step 1: Create reel container
        container_data = {
            "media_type": "REELS",
            "video_url": video_url,
            "share_to_feed": str(share_to_feed).lower(),
            "access_token": self.access_token,
        }
        if caption:
            container_data["caption"] = caption

        resp = requests.post(
            f"{GRAPH_API_BASE}/{self.account_id}/media",
            data=container_data,
        )
        if resp.status_code != 200:
            return {"error": f"Reel container failed: {resp.status_code}", "detail": resp.json()}

        container_id = resp.json().get("id")

        # Step 2: Poll until ready
        for _ in range(30):
            time.sleep(10)
            status_resp = requests.get(
                f"{GRAPH_API_BASE}/{container_id}",
                params={"fields": "status_code", "access_token": self.access_token},
            )
            if status_resp.status_code == 200:
                status = status_resp.json().get("status_code")
                if status == "FINISHED":
                    break
                elif status == "ERROR":
                    return {"error": "Reel processing failed", "detail": status_resp.json()}

        # Step 3: Publish
        pub_resp = requests.post(
            f"{GRAPH_API_BASE}/{self.account_id}/media_publish",
            data={"creation_id": container_id, "access_token": self.access_token},
        )
        if pub_resp.status_code == 200:
            return {"success": True, "media_id": pub_resp.json().get("id")}
        return {"error": f"Publish failed: {pub_resp.status_code}", "detail": pub_resp.json()}

    def get_media(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent media from the account.

        Args:
            limit: Number of items (max 100).
        """
        if not self.access_token or not self.account_id:
            return {"error": "Access token and account ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        resp = requests.get(
            f"{GRAPH_API_BASE}/{self.account_id}/media",
            params={
                "fields": "id,caption,media_type,media_url,timestamp,permalink",
                "limit": min(limit, 100),
                "access_token": self.access_token,
            },
        )
        if resp.status_code == 200:
            return {"success": True, "media": resp.json().get("data", [])}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def get_account_info(self) -> Dict[str, Any]:
        """Get Instagram account information."""
        if not self.access_token or not self.account_id:
            return {"error": "Access token and account ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        resp = requests.get(
            f"{GRAPH_API_BASE}/{self.account_id}",
            params={
                "fields": "id,username,name,biography,followers_count,follows_count,media_count",
                "access_token": self.access_token,
            },
        )
        if resp.status_code == 200:
            return {"success": True, "account": resp.json()}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}


# Standalone functions for agent discoverability
def instagram_post_image(
    image_url: str,
    caption: str = "",
    access_token: Optional[str] = None,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Post an image to Instagram (Business/Creator account).

    Args:
        image_url: Public URL of the image.
        caption: Post caption.
        access_token: Meta Graph API token (or set INSTAGRAM_ACCESS_TOKEN env var).
        account_id: Instagram Business account ID (or set INSTAGRAM_BUSINESS_ACCOUNT_ID env var).
    """
    return InstagramTool(access_token=access_token, account_id=account_id).post_image(
        image_url=image_url, caption=caption
    )


def instagram_post_carousel(
    image_urls: List[str],
    caption: str = "",
    access_token: Optional[str] = None,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Post a carousel (2-10 images) to Instagram.

    Args:
        image_urls: List of public image URLs.
        caption: Post caption.
        access_token: Meta Graph API token.
        account_id: Instagram Business account ID.
    """
    return InstagramTool(access_token=access_token, account_id=account_id).post_carousel(
        image_urls=image_urls, caption=caption
    )


def instagram_post_reel(
    video_url: str,
    caption: str = "",
    access_token: Optional[str] = None,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Post a Reel (short video) to Instagram.

    Args:
        video_url: Public URL of the video (MP4, max 90s).
        caption: Reel caption.
        access_token: Meta Graph API token.
        account_id: Instagram Business account ID.
    """
    return InstagramTool(access_token=access_token, account_id=account_id).post_reel(
        video_url=video_url, caption=caption
    )


def instagram_get_media(
    limit: int = 10,
    access_token: Optional[str] = None,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get recent media from Instagram account.

    Args:
        limit: Number of items.
        access_token: Meta Graph API token.
        account_id: Instagram Business account ID.
    """
    return InstagramTool(access_token=access_token, account_id=account_id).get_media(limit=limit)


def instagram_get_account_info(
    access_token: Optional[str] = None,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get Instagram account information.

    Args:
        access_token: Meta Graph API token.
        account_id: Instagram Business account ID.
    """
    return InstagramTool(access_token=access_token, account_id=account_id).get_account_info()
