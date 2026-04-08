"""Facebook Tool for PraisonAI Agents.

Post to Facebook Pages using the Graph API.

Usage:
    from praisonai_tools import FacebookTool

    fb = FacebookTool()
    fb.post_text("Hello from PraisonAI!")

Environment Variables:
    FACEBOOK_PAGE_ACCESS_TOKEN: Page access token
    FACEBOOK_PAGE_ID: Facebook page ID
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v20.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class FacebookTool(BaseTool):
    """Tool for Facebook Page operations."""

    name = "facebook"
    description = "Post content to Facebook Pages."

    def __init__(
        self,
        page_access_token: Optional[str] = None,
        page_id: Optional[str] = None,
    ):
        self.page_access_token = page_access_token or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
        self.page_id = page_id or os.getenv("FACEBOOK_PAGE_ID")
        super().__init__()

    def run(self, action: str = "post_text", text: Optional[str] = None, **kwargs):
        action = action.lower().replace("-", "_")
        if action == "post_text":
            return self.post_text(text=text, **kwargs)
        elif action == "post_image":
            return self.post_image(text=text, **kwargs)
        elif action == "post_link":
            return self.post_link(text=text, **kwargs)
        elif action == "get_page_info":
            return self.get_page_info()
        handler = getattr(self, action, None)
        if handler and callable(handler) and not action.startswith("_"):
            return handler(**kwargs)
        return {"error": f"Unknown action: {action}"}

    def post_text(self, text: str, page_id: str = "") -> Dict[str, Any]:
        """Post a text update to a Facebook Page.

        Args:
            text: Post message.
            page_id: Override page ID (or uses default).
        """
        if not text:
            return {"error": "text is required"}
        if not self.page_access_token:
            return {"error": "FACEBOOK_PAGE_ACCESS_TOKEN required"}

        pid = page_id or self.page_id
        if not pid:
            return {"error": "FACEBOOK_PAGE_ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. pip install requests"}

        resp = requests.post(
            f"{GRAPH_API_BASE}/{pid}/feed",
            data={"message": text, "access_token": self.page_access_token},
        )
        if resp.status_code == 200:
            return {"success": True, "post_id": resp.json().get("id")}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def post_image(
        self,
        text: str = "",
        image_url: str = "",
        image_path: str = "",
        page_id: str = "",
    ) -> Dict[str, Any]:
        """Post an image to a Facebook Page.

        Args:
            text: Caption text.
            image_url: Public URL of image.
            image_path: Local file path.
            page_id: Override page ID.
        """
        if not image_url and not image_path:
            return {"error": "image_url or image_path is required"}
        if not self.page_access_token:
            return {"error": "FACEBOOK_PAGE_ACCESS_TOKEN required"}

        pid = page_id or self.page_id
        if not pid:
            return {"error": "FACEBOOK_PAGE_ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        url = f"{GRAPH_API_BASE}/{pid}/photos"
        data = {"access_token": self.page_access_token}
        if text:
            data["message"] = text

        if image_path and os.path.isfile(image_path):
            with open(image_path, "rb") as f:
                resp = requests.post(url, data=data, files={"source": f})
        elif image_url:
            data["url"] = image_url
            resp = requests.post(url, data=data)
        else:
            return {"error": "Could not read image"}

        if resp.status_code == 200:
            return {"success": True, "post_id": resp.json().get("post_id"), "photo_id": resp.json().get("id")}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def post_link(
        self,
        text: str = "",
        link: str = "",
        page_id: str = "",
    ) -> Dict[str, Any]:
        """Post a link to a Facebook Page.

        Args:
            text: Post message.
            link: URL to share.
            page_id: Override page ID.
        """
        if not link:
            return {"error": "link is required"}
        if not self.page_access_token:
            return {"error": "FACEBOOK_PAGE_ACCESS_TOKEN required"}

        pid = page_id or self.page_id
        if not pid:
            return {"error": "FACEBOOK_PAGE_ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        data = {"link": link, "access_token": self.page_access_token}
        if text:
            data["message"] = text

        resp = requests.post(f"{GRAPH_API_BASE}/{pid}/feed", data=data)
        if resp.status_code == 200:
            return {"success": True, "post_id": resp.json().get("id")}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def post_video(
        self,
        text: str = "",
        video_url: str = "",
        video_path: str = "",
        title: str = "",
        page_id: str = "",
    ) -> Dict[str, Any]:
        """Post a video to a Facebook Page.

        Args:
            text: Video description.
            video_url: Public URL of video.
            video_path: Local file path.
            title: Video title.
            page_id: Override page ID.
        """
        if not video_url and not video_path:
            return {"error": "video_url or video_path is required"}
        if not self.page_access_token:
            return {"error": "FACEBOOK_PAGE_ACCESS_TOKEN required"}

        pid = page_id or self.page_id
        if not pid:
            return {"error": "FACEBOOK_PAGE_ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        url = f"{GRAPH_API_BASE}/{pid}/videos"
        data = {"access_token": self.page_access_token}
        if text:
            data["description"] = text
        if title:
            data["title"] = title

        if video_path and os.path.isfile(video_path):
            with open(video_path, "rb") as f:
                resp = requests.post(url, data=data, files={"source": f})
        elif video_url:
            data["file_url"] = video_url
            resp = requests.post(url, data=data)
        else:
            return {"error": "Could not read video"}

        if resp.status_code == 200:
            return {"success": True, "video_id": resp.json().get("id")}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def get_page_info(self, page_id: str = "") -> Dict[str, Any]:
        """Get Facebook Page information.

        Args:
            page_id: Override page ID.
        """
        if not self.page_access_token:
            return {"error": "FACEBOOK_PAGE_ACCESS_TOKEN required"}

        pid = page_id or self.page_id
        if not pid:
            return {"error": "FACEBOOK_PAGE_ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        resp = requests.get(
            f"{GRAPH_API_BASE}/{pid}",
            params={
                "fields": "id,name,category,fan_count,about,website",
                "access_token": self.page_access_token,
            },
        )
        if resp.status_code == 200:
            return {"success": True, "page": resp.json()}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def get_posts(self, page_id: str = "", limit: int = 10) -> Dict[str, Any]:
        """Get recent posts from a Facebook Page.

        Args:
            page_id: Override page ID.
            limit: Number of posts to retrieve (max 100).
        """
        if not self.page_access_token:
            return {"error": "FACEBOOK_PAGE_ACCESS_TOKEN required"}

        pid = page_id or self.page_id
        if not pid:
            return {"error": "FACEBOOK_PAGE_ID required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        resp = requests.get(
            f"{GRAPH_API_BASE}/{pid}/posts",
            params={
                "fields": "id,message,created_time,type,permalink_url",
                "limit": min(limit, 100),
                "access_token": self.page_access_token,
            },
        )
        if resp.status_code == 200:
            return {"success": True, "posts": resp.json().get("data", [])}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def delete_post(self, post_id: str) -> Dict[str, Any]:
        """Delete a Facebook post.

        Args:
            post_id: Post ID to delete.
        """
        if not post_id:
            return {"error": "post_id is required"}
        if not self.page_access_token:
            return {"error": "FACEBOOK_PAGE_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        resp = requests.delete(
            f"{GRAPH_API_BASE}/{post_id}",
            params={"access_token": self.page_access_token},
        )
        if resp.status_code == 200:
            return {"success": True}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}


# Standalone functions for agent discoverability
def facebook_post_text(
    text: str,
    page_id: str = "",
    page_access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Post a text update to a Facebook Page.

    Args:
        text: Post message.
        page_id: Facebook page ID (or set FACEBOOK_PAGE_ID env var).
        page_access_token: Page token (or set FACEBOOK_PAGE_ACCESS_TOKEN env var).
    """
    return FacebookTool(page_access_token=page_access_token, page_id=page_id or None).post_text(text=text)


def facebook_post_image(
    image_url: str = "",
    image_path: str = "",
    text: str = "",
    page_id: str = "",
    page_access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Post an image to a Facebook Page.

    Args:
        image_url: Public URL of image.
        image_path: Local file path.
        text: Caption text.
        page_id: Facebook page ID.
        page_access_token: Page token.
    """
    return FacebookTool(page_access_token=page_access_token, page_id=page_id or None).post_image(
        text=text, image_url=image_url, image_path=image_path
    )


def facebook_post_link(
    link: str,
    text: str = "",
    page_id: str = "",
    page_access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Post a link to a Facebook Page.

    Args:
        link: URL to share.
        text: Post message.
        page_id: Facebook page ID.
        page_access_token: Page token.
    """
    return FacebookTool(page_access_token=page_access_token, page_id=page_id or None).post_link(
        text=text, link=link
    )


def facebook_post_video(
    video_url: str = "",
    video_path: str = "",
    text: str = "",
    title: str = "",
    page_id: str = "",
    page_access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Post a video to a Facebook Page.

    Args:
        video_url: Public URL of video.
        video_path: Local file path.
        text: Video description.
        title: Video title.
        page_id: Facebook page ID.
        page_access_token: Page token.
    """
    return FacebookTool(page_access_token=page_access_token, page_id=page_id or None).post_video(
        text=text, video_url=video_url, video_path=video_path, title=title
    )


def facebook_get_page_info(
    page_id: str = "",
    page_access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Get Facebook Page information.

    Args:
        page_id: Facebook page ID.
        page_access_token: Page token.
    """
    return FacebookTool(page_access_token=page_access_token, page_id=page_id or None).get_page_info()


def facebook_delete_post(
    post_id: str,
    page_access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete a Facebook post.

    Args:
        post_id: Post ID to delete.
        page_access_token: Page token.
    """
    return FacebookTool(page_access_token=page_access_token).delete_post(post_id=post_id)
