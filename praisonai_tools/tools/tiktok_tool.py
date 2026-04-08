"""TikTok Tool for PraisonAI Agents.

Post videos to TikTok using the official Content Posting API.

Usage:
    from praisonai_tools import TikTokTool

    tt = TikTokTool()
    tt.post_video(video_url="https://example.com/video.mp4", title="My Video")

Environment Variables:
    TIKTOK_ACCESS_TOKEN: OAuth 2.0 access token
"""

import os
import time
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

API_BASE = "https://open.tiktokapis.com/v2"


class TikTokTool(BaseTool):
    """Tool for TikTok Content Posting API operations."""

    name = "tiktok"
    description = "Post videos to TikTok."

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("TIKTOK_ACCESS_TOKEN")
        super().__init__()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    def run(self, action: str = "post_video", **kwargs):
        action = action.lower().replace("-", "_")
        handler = getattr(self, action, None)
        if handler and callable(handler) and not action.startswith("_"):
            return handler(**kwargs)
        return {"error": f"Unknown action: {action}"}

    def get_creator_info(self) -> Dict[str, Any]:
        """Get creator info and posting permissions."""
        if not self.access_token:
            return {"error": "TIKTOK_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. pip install requests"}

        resp = requests.post(
            f"{API_BASE}/post/publish/creator_info/query/",
            headers=self._headers(),
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("error", {}).get("code") == "ok":
                return {"success": True, "creator_info": data.get("data", {})}
            return {"error": data.get("error", {}).get("message", "Unknown error")}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.text}

    def post_video(
        self,
        video_url: str = "",
        video_path: str = "",
        title: str = "",
        privacy_level: str = "SELF_ONLY",
        disable_duet: bool = False,
        disable_comment: bool = False,
        disable_stitch: bool = False,
        brand_content_toggle: bool = False,
        brand_organic_toggle: bool = False,
    ) -> Dict[str, Any]:
        """Post a video to TikTok.

        Args:
            video_url: Public URL of the video (use PULL_FROM_URL).
            video_path: Local file path (use FILE_UPLOAD).
            title: Video title/caption (max 150 chars).
            privacy_level: SELF_ONLY, MUTUAL_FOLLOW_FRIENDS, FOLLOWER_OF_CREATOR, PUBLIC_TO_EVERYONE.
            disable_duet: Disable duet.
            disable_comment: Disable comments.
            disable_stitch: Disable stitch.
            brand_content_toggle: Mark as branded content.
            brand_organic_toggle: Mark as organic branded content.
        """
        if not video_url and not video_path:
            return {"error": "video_url or video_path is required"}
        if not self.access_token:
            return {"error": "TIKTOK_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        # Determine source type
        if video_url:
            source_info = {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            }
        else:
            # For file upload, we need a two-step process
            source_info = {
                "source": "FILE_UPLOAD",
                "video_size": os.path.getsize(video_path) if os.path.isfile(video_path) else 0,
                "chunk_size": os.path.getsize(video_path) if os.path.isfile(video_path) else 0,
                "total_chunk_count": 1,
            }

        post_info = {
            "privacy_level": privacy_level,
            "disable_duet": disable_duet,
            "disable_comment": disable_comment,
            "disable_stitch": disable_stitch,
            "brand_content_toggle": brand_content_toggle,
            "brand_organic_toggle": brand_organic_toggle,
        }
        if title:
            post_info["title"] = title[:150]

        payload = {
            "post_info": post_info,
            "source_info": source_info,
        }

        resp = requests.post(
            f"{API_BASE}/post/publish/video/init/",
            headers=self._headers(),
            json=payload,
        )

        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}", "detail": resp.text}

        data = resp.json()
        if data.get("error", {}).get("code") != "ok":
            return {"error": data.get("error", {}).get("message", "Unknown error"), "detail": data}

        publish_id = data.get("data", {}).get("publish_id", "")
        upload_url = data.get("data", {}).get("upload_url", "")

        # If file upload, upload the video binary
        if video_path and upload_url and os.path.isfile(video_path):
            with open(video_path, "rb") as f:
                upload_resp = requests.put(
                    upload_url,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Range": f"bytes 0-{os.path.getsize(video_path) - 1}/{os.path.getsize(video_path)}",
                    },
                    data=f,
                )
                if upload_resp.status_code not in (200, 201):
                    return {"error": f"Upload failed: {upload_resp.status_code}", "detail": upload_resp.text}

        return {"success": True, "publish_id": publish_id}

    def get_post_status(self, publish_id: str) -> Dict[str, Any]:
        """Check the status of a published video.

        Args:
            publish_id: Publish ID from post_video result.
        """
        if not publish_id:
            return {"error": "publish_id is required"}
        if not self.access_token:
            return {"error": "TIKTOK_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        resp = requests.post(
            f"{API_BASE}/post/publish/status/fetch/",
            headers=self._headers(),
            json={"publish_id": publish_id},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("error", {}).get("code") == "ok":
                return {"success": True, "status": data.get("data", {})}
            return {"error": data.get("error", {}).get("message")}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.text}

    def post_photo(
        self,
        photo_urls: List[str] = None,
        title: str = "",
        privacy_level: str = "SELF_ONLY",
        disable_comment: bool = False,
    ) -> Dict[str, Any]:
        """Post photos to TikTok.

        Args:
            photo_urls: List of public image URLs (1-35 images).
            title: Photo post caption.
            privacy_level: Privacy level.
            disable_comment: Disable comments.
        """
        if not photo_urls:
            return {"error": "photo_urls is required (list of URLs)"}
        if not self.access_token:
            return {"error": "TIKTOK_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        post_info = {
            "privacy_level": privacy_level,
            "disable_comment": disable_comment,
        }
        if title:
            post_info["title"] = title[:150]

        payload = {
            "post_info": post_info,
            "source_info": {
                "source": "PULL_FROM_URL",
                "photo_cover_index": 0,
                "photo_images": photo_urls,
            },
            "post_mode": "DIRECT_POST",
            "media_type": "PHOTO",
        }

        resp = requests.post(
            f"{API_BASE}/post/publish/content/init/",
            headers=self._headers(),
            json=payload,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("error", {}).get("code") == "ok":
                return {"success": True, "publish_id": data.get("data", {}).get("publish_id")}
            return {"error": data.get("error", {}).get("message"), "detail": data}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.text}


# Standalone functions for agent discoverability
def tiktok_post_video(
    video_url: str = "",
    video_path: str = "",
    title: str = "",
    privacy_level: str = "SELF_ONLY",
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Post a video to TikTok.

    Args:
        video_url: Public URL of the video.
        video_path: Local file path.
        title: Video title/caption (max 150 chars).
        privacy_level: SELF_ONLY, MUTUAL_FOLLOW_FRIENDS, FOLLOWER_OF_CREATOR, PUBLIC_TO_EVERYONE.
        access_token: OAuth token (or set TIKTOK_ACCESS_TOKEN env var).
    """
    return TikTokTool(access_token=access_token).post_video(
        video_url=video_url, video_path=video_path, title=title, privacy_level=privacy_level
    )


def tiktok_post_photo(
    photo_urls: List[str] = None,
    title: str = "",
    privacy_level: str = "SELF_ONLY",
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Post photos to TikTok.

    Args:
        photo_urls: List of public image URLs (1-35 images).
        title: Photo post caption.
        privacy_level: Privacy level.
        access_token: OAuth token (or set TIKTOK_ACCESS_TOKEN env var).
    """
    return TikTokTool(access_token=access_token).post_photo(
        photo_urls=photo_urls, title=title, privacy_level=privacy_level
    )


def tiktok_get_creator_info(
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Get TikTok creator info and posting permissions.

    Args:
        access_token: OAuth token (or set TIKTOK_ACCESS_TOKEN env var).
    """
    return TikTokTool(access_token=access_token).get_creator_info()


def tiktok_get_post_status(
    publish_id: str,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Check the status of a TikTok post.

    Args:
        publish_id: Publish ID from post_video/post_photo result.
        access_token: OAuth token (or set TIKTOK_ACCESS_TOKEN env var).
    """
    return TikTokTool(access_token=access_token).get_post_status(publish_id=publish_id)
