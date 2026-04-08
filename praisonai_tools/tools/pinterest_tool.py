"""Pinterest Tool for PraisonAI Agents.

Create pins on Pinterest using the official API v5.

Usage:
    from praisonai_tools import PinterestTool

    p = PinterestTool()
    p.create_pin(board_id="123", title="My Pin", image_url="https://example.com/img.jpg")

Environment Variables:
    PINTEREST_ACCESS_TOKEN: Pinterest OAuth 2.0 access token
"""

import os
import time
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

API_BASE = "https://api.pinterest.com/v5"


class PinterestTool(BaseTool):
    """Tool for Pinterest API v5 operations."""

    name = "pinterest"
    description = "Create pins and manage boards on Pinterest."

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("PINTEREST_ACCESS_TOKEN")
        super().__init__()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def run(self, action: str = "create_pin", **kwargs):
        action = action.lower().replace("-", "_")
        handler = getattr(self, action, None)
        if handler and callable(handler) and not action.startswith("_"):
            return handler(**kwargs)
        return {"error": f"Unknown action: {action}"}

    def create_pin(
        self,
        board_id: str,
        title: str = "",
        description: str = "",
        image_url: str = "",
        image_base64: str = "",
        link: str = "",
        alt_text: str = "",
        note: str = "",
    ) -> Dict[str, Any]:
        """Create a pin on Pinterest.

        Args:
            board_id: Board ID to pin to (from list_boards).
            title: Pin title (max 100 chars).
            description: Pin description (max 800 chars).
            image_url: Public URL of image.
            image_base64: Base64-encoded image data.
            link: Destination URL when pin is clicked.
            alt_text: Alt text for accessibility.
            note: Pin note.
        """
        if not board_id:
            return {"error": "board_id is required (use list_boards to find your boards)"}
        if not image_url and not image_base64:
            return {"error": "image_url or image_base64 is required"}
        if not self.access_token:
            return {"error": "PINTEREST_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. pip install requests"}

        data = {"board_id": board_id}
        if title:
            data["title"] = title[:100]
        if description:
            data["description"] = description[:800]
        if link:
            data["link"] = link
        if alt_text:
            data["alt_text"] = alt_text
        if note:
            data["note"] = note

        if image_url:
            data["media_source"] = {"source_type": "image_url", "url": image_url}
        elif image_base64:
            data["media_source"] = {"source_type": "image_base64", "data": image_base64, "content_type": "image/png"}

        resp = requests.post(f"{API_BASE}/pins", headers=self._headers(), json=data)
        if resp.status_code in (200, 201):
            result = resp.json()
            return {"success": True, "pin_id": result.get("id"), "pin": result}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def create_video_pin(
        self,
        board_id: str,
        video_url: str = "",
        cover_image_url: str = "",
        title: str = "",
        description: str = "",
        link: str = "",
    ) -> Dict[str, Any]:
        """Create a video pin on Pinterest.

        Args:
            board_id: Board ID.
            video_url: URL of the video to upload.
            cover_image_url: Cover image URL.
            title: Pin title.
            description: Pin description.
            link: Destination URL.
        """
        if not board_id:
            return {"error": "board_id is required"}
        if not self.access_token:
            return {"error": "PINTEREST_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        # Step 1: Register media
        media_data = {"media_type": "video"}
        media_resp = requests.post(f"{API_BASE}/media", headers=self._headers(), json=media_data)
        if media_resp.status_code not in (200, 201):
            return {"error": f"Media registration failed: {media_resp.status_code}", "detail": media_resp.json()}

        media_result = media_resp.json()
        media_id = media_result.get("media_id")
        upload_url = media_result.get("upload_url")

        # Step 2: Upload video
        if video_url and upload_url:
            video_data = requests.get(video_url).content
            upload_resp = requests.put(upload_url, data=video_data, headers={"Content-Type": "video/mp4"})
            if upload_resp.status_code not in (200, 201, 204):
                return {"error": f"Video upload failed: {upload_resp.status_code}"}

        # Step 3: Wait for processing
        for _ in range(30):
            time.sleep(10)
            status_resp = requests.get(f"{API_BASE}/media/{media_id}", headers=self._headers())
            if status_resp.status_code == 200:
                status = status_resp.json().get("status")
                if status == "succeeded":
                    break
                elif status == "failed":
                    return {"error": "Video processing failed"}

        # Step 4: Create pin with video
        pin_data = {"board_id": board_id, "media_source": {"source_type": "video_id", "media_id": media_id}}
        if title:
            pin_data["title"] = title
        if description:
            pin_data["description"] = description
        if link:
            pin_data["link"] = link
        if cover_image_url:
            pin_data["media_source"]["cover_image_url"] = cover_image_url

        resp = requests.post(f"{API_BASE}/pins", headers=self._headers(), json=pin_data)
        if resp.status_code in (200, 201):
            return {"success": True, "pin_id": resp.json().get("id")}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def list_boards(self, page_size: int = 25) -> Dict[str, Any]:
        """List the user's boards.

        Args:
            page_size: Number of boards to return (max 250).
        """
        if not self.access_token:
            return {"error": "PINTEREST_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        resp = requests.get(
            f"{API_BASE}/boards",
            headers=self._headers(),
            params={"page_size": min(page_size, 250)},
        )
        if resp.status_code == 200:
            return {"success": True, "boards": resp.json().get("items", [])}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def get_pin(self, pin_id: str) -> Dict[str, Any]:
        """Get pin details.

        Args:
            pin_id: Pin ID.
        """
        if not pin_id:
            return {"error": "pin_id is required"}
        if not self.access_token:
            return {"error": "PINTEREST_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        resp = requests.get(f"{API_BASE}/pins/{pin_id}", headers=self._headers())
        if resp.status_code == 200:
            return {"success": True, "pin": resp.json()}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def delete_pin(self, pin_id: str) -> Dict[str, Any]:
        """Delete a pin.

        Args:
            pin_id: Pin ID to delete.
        """
        if not pin_id:
            return {"error": "pin_id is required"}
        if not self.access_token:
            return {"error": "PINTEREST_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        resp = requests.delete(f"{API_BASE}/pins/{pin_id}", headers=self._headers())
        if resp.status_code in (200, 204):
            return {"success": True}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.text}

    def get_account_info(self) -> Dict[str, Any]:
        """Get Pinterest account info."""
        if not self.access_token:
            return {"error": "PINTEREST_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        resp = requests.get(f"{API_BASE}/user_account", headers=self._headers())
        if resp.status_code == 200:
            return {"success": True, "account": resp.json()}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}


# Standalone functions
def pinterest_create_pin(
    board_id: str,
    image_url: str = "",
    title: str = "",
    description: str = "",
    link: str = "",
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a pin on Pinterest.

    Args:
        board_id: Board ID (use pinterest_list_boards to find).
        image_url: Public URL of image.
        title: Pin title.
        description: Pin description.
        link: Destination URL.
        access_token: OAuth token (or set PINTEREST_ACCESS_TOKEN env var).
    """
    return PinterestTool(access_token=access_token).create_pin(
        board_id=board_id, image_url=image_url, title=title, description=description, link=link
    )


def pinterest_list_boards(
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List Pinterest boards.

    Args:
        access_token: OAuth token (or set PINTEREST_ACCESS_TOKEN env var).
    """
    return PinterestTool(access_token=access_token).list_boards()


def pinterest_get_pin(
    pin_id: str,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Get pin details.

    Args:
        pin_id: Pin ID.
        access_token: OAuth token.
    """
    return PinterestTool(access_token=access_token).get_pin(pin_id=pin_id)


def pinterest_delete_pin(
    pin_id: str,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete a Pinterest pin.

    Args:
        pin_id: Pin ID.
        access_token: OAuth token.
    """
    return PinterestTool(access_token=access_token).delete_pin(pin_id=pin_id)


def pinterest_get_account_info(
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Get Pinterest account info.

    Args:
        access_token: OAuth token.
    """
    return PinterestTool(access_token=access_token).get_account_info()
