"""Medium Tool for PraisonAI Agents.

Publish posts to Medium using the official REST API.

Usage:
    from praisonai_tools import MediumTool

    m = MediumTool()
    m.publish_post(title="My Post", content="# Hello World", content_format="markdown")

Environment Variables:
    MEDIUM_TOKEN: Medium integration token (Settings > Security > Integration tokens)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

API_BASE = "https://api.medium.com/v1"


class MediumTool(BaseTool):
    """Tool for Medium API operations."""

    name = "medium"
    description = "Publish posts to Medium."

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("MEDIUM_TOKEN")
        self._user_id = None
        super().__init__()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def run(self, action: str = "publish_post", **kwargs):
        action = action.lower().replace("-", "_")
        handler = getattr(self, action, None)
        if handler and callable(handler) and not action.startswith("_"):
            return handler(**kwargs)
        return {"error": f"Unknown action: {action}"}

    def get_user(self) -> Dict[str, Any]:
        """Get the authenticated Medium user info."""
        if not self.token:
            return {"error": "MEDIUM_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. pip install requests"}

        resp = requests.get(f"{API_BASE}/me", headers=self._headers())
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            self._user_id = data.get("id")
            return {"success": True, "user": data}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def _get_user_id(self) -> Optional[str]:
        if self._user_id:
            return self._user_id
        result = self.get_user()
        if result.get("success"):
            return self._user_id
        return None

    def publish_post(
        self,
        title: str,
        content: str,
        content_format: str = "markdown",
        tags: Optional[List[str]] = None,
        publish_status: str = "draft",
        canonical_url: str = "",
        notify_followers: bool = False,
    ) -> Dict[str, Any]:
        """Publish a post to Medium.

        Args:
            title: Post title.
            content: Post body (markdown or HTML).
            content_format: 'markdown' or 'html'.
            tags: List of tags (max 5).
            publish_status: 'draft', 'public', or 'unlisted'.
            canonical_url: Original article URL for SEO.
            notify_followers: Notify followers of publication.
        """
        if not title:
            return {"error": "title is required"}
        if not content:
            return {"error": "content is required"}
        if not self.token:
            return {"error": "MEDIUM_TOKEN required"}

        # LLM fallback: empty strings → defaults
        content_format = content_format or "markdown"
        publish_status = publish_status or "draft"

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        user_id = self._get_user_id()
        if not user_id:
            return {"error": "Could not retrieve user ID — check MEDIUM_TOKEN"}

        data = {
            "title": title,
            "contentFormat": content_format,
            "content": content,
            "publishStatus": publish_status,
            "notifyFollowers": notify_followers,
        }
        if tags:
            data["tags"] = tags[:5]
        if canonical_url:
            data["canonicalUrl"] = canonical_url

        resp = requests.post(
            f"{API_BASE}/users/{user_id}/posts",
            headers=self._headers(),
            json=data,
        )
        if resp.status_code in (200, 201):
            post_data = resp.json().get("data", {})
            return {
                "success": True,
                "post_id": post_data.get("id"),
                "url": post_data.get("url"),
                "publish_status": post_data.get("publishStatus"),
                "title": post_data.get("title"),
            }
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def publish_to_publication(
        self,
        publication_id: str,
        title: str,
        content: str,
        content_format: str = "markdown",
        tags: Optional[List[str]] = None,
        publish_status: str = "draft",
        canonical_url: str = "",
        notify_followers: bool = False,
    ) -> Dict[str, Any]:
        """Publish a post to a Medium publication.

        Args:
            publication_id: Publication ID.
            title: Post title.
            content: Post body.
            content_format: 'markdown' or 'html'.
            tags: List of tags (max 5).
            publish_status: 'draft', 'public', or 'unlisted'.
            canonical_url: Original article URL.
            notify_followers: Notify followers.
        """
        if not publication_id:
            return {"error": "publication_id is required"}
        if not title or not content:
            return {"error": "title and content are required"}
        if not self.token:
            return {"error": "MEDIUM_TOKEN required"}

        content_format = content_format or "markdown"
        publish_status = publish_status or "draft"

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        data = {
            "title": title,
            "contentFormat": content_format,
            "content": content,
            "publishStatus": publish_status,
            "notifyFollowers": notify_followers,
        }
        if tags:
            data["tags"] = tags[:5]
        if canonical_url:
            data["canonicalUrl"] = canonical_url

        resp = requests.post(
            f"{API_BASE}/publications/{publication_id}/posts",
            headers=self._headers(),
            json=data,
        )
        if resp.status_code in (200, 201):
            post_data = resp.json().get("data", {})
            return {"success": True, "post_id": post_data.get("id"), "url": post_data.get("url")}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}

    def list_publications(self) -> Dict[str, Any]:
        """List publications the user contributes to."""
        if not self.token:
            return {"error": "MEDIUM_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        user_id = self._get_user_id()
        if not user_id:
            return {"error": "Could not retrieve user ID"}

        resp = requests.get(
            f"{API_BASE}/users/{user_id}/publications",
            headers=self._headers(),
        )
        if resp.status_code == 200:
            return {"success": True, "publications": resp.json().get("data", [])}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json()}


# Standalone functions
def medium_publish_post(
    title: str,
    content: str,
    content_format: str = "markdown",
    tags: Optional[List[str]] = None,
    publish_status: str = "draft",
    canonical_url: str = "",
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish a post to Medium.

    Args:
        title: Post title.
        content: Post body (markdown or HTML).
        content_format: 'markdown' or 'html'.
        tags: List of tags (max 5).
        publish_status: 'draft', 'public', or 'unlisted'.
        canonical_url: Original article URL for SEO.
        token: Medium integration token (or set MEDIUM_TOKEN env var).
    """
    return MediumTool(token=token).publish_post(
        title=title, content=content, content_format=content_format,
        tags=tags, publish_status=publish_status, canonical_url=canonical_url,
    )


def medium_get_user(
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Get Medium user info.

    Args:
        token: Medium integration token (or set MEDIUM_TOKEN env var).
    """
    return MediumTool(token=token).get_user()


def medium_list_publications(
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """List Medium publications the user contributes to.

    Args:
        token: Medium integration token (or set MEDIUM_TOKEN env var).
    """
    return MediumTool(token=token).list_publications()


def medium_publish_to_publication(
    publication_id: str,
    title: str,
    content: str,
    content_format: str = "markdown",
    tags: Optional[List[str]] = None,
    publish_status: str = "draft",
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish a post to a Medium publication.

    Args:
        publication_id: Publication ID.
        title: Post title.
        content: Post body (markdown or HTML).
        content_format: 'markdown' or 'html'.
        tags: List of tags (max 5).
        publish_status: 'draft', 'public', or 'unlisted'.
        token: Medium integration token (or set MEDIUM_TOKEN env var).
    """
    return MediumTool(token=token).publish_to_publication(
        publication_id=publication_id, title=title, content=content,
        content_format=content_format, tags=tags, publish_status=publish_status,
    )
