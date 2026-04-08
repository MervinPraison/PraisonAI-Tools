"""LinkedIn Tool for PraisonAI Agents.

Post to LinkedIn using the official REST API.

Usage:
    from praisonai_tools import LinkedInTool

    li = LinkedInTool()
    li.post_text("Hello from PraisonAI!")

Environment Variables:
    LINKEDIN_ACCESS_TOKEN: OAuth 2.0 bearer token
    LINKEDIN_PERSON_URN: Your person URN (e.g. "abc123" from urn:li:person:abc123)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

API_BASE = "https://api.linkedin.com/rest"
API_VERSION = "202503"


class LinkedInTool(BaseTool):
    """Tool for LinkedIn operations."""

    name = "linkedin"
    description = "Post content to LinkedIn."

    def __init__(
        self,
        access_token: Optional[str] = None,
        person_urn: Optional[str] = None,
        organization_urn: Optional[str] = None,
    ):
        self.access_token = access_token or os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.person_urn = person_urn or os.getenv("LINKEDIN_PERSON_URN")
        self.organization_urn = organization_urn or os.getenv("LINKEDIN_ORGANIZATION_URN")
        super().__init__()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _author_urn(self, as_org: bool = False) -> str:
        if as_org and self.organization_urn:
            return f"urn:li:organization:{self.organization_urn}"
        return f"urn:li:person:{self.person_urn}"

    def run(self, action: str = "post_text", text: Optional[str] = None, **kwargs):
        action = action.lower().replace("-", "_")
        if action == "post_text":
            return self.post_text(text=text, **kwargs)
        elif action == "post_image":
            return self.post_image(text=text, **kwargs)
        elif action == "post_article":
            return self.post_article(text=text, **kwargs)
        elif action == "get_profile":
            return self.get_profile()
        handler = getattr(self, action, None)
        if handler and callable(handler) and not action.startswith("_"):
            return handler(**kwargs)
        return {"error": f"Unknown action: {action}"}

    def post_text(
        self,
        text: str,
        visibility: str = "PUBLIC",
        as_org: bool = False,
    ) -> Dict[str, Any]:
        """Post a text update to LinkedIn.

        Args:
            text: Post content (max 3000 chars).
            visibility: 'PUBLIC' or 'CONNECTIONS'.
            as_org: Post as organization instead of person.
        """
        if not text:
            return {"error": "text is required"}
        if not self.access_token:
            return {"error": "LINKEDIN_ACCESS_TOKEN required"}
        if not self.person_urn and not (as_org and self.organization_urn):
            return {"error": "LINKEDIN_PERSON_URN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. pip install requests"}

        data = {
            "author": self._author_urn(as_org),
            "commentary": text,
            "visibility": visibility,
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        resp = requests.post(f"{API_BASE}/posts", headers=self._headers(), json=data)
        if resp.status_code in (200, 201):
            post_id = resp.headers.get("x-restli-id", "")
            return {"success": True, "post_id": post_id}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.json() if resp.text else resp.text}

    def post_image(
        self,
        text: str,
        image_url: str = "",
        image_path: str = "",
        title: str = "",
        as_org: bool = False,
    ) -> Dict[str, Any]:
        """Post with an image to LinkedIn.

        Args:
            text: Post text.
            image_url: Public URL of image (use this or image_path).
            image_path: Local file path to upload.
            title: Image title.
            as_org: Post as organization.
        """
        if not text:
            return {"error": "text is required"}
        if not image_url and not image_path:
            return {"error": "image_url or image_path is required"}
        if not self.access_token:
            return {"error": "LINKEDIN_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        author = self._author_urn(as_org)

        # Step 1: Initialize image upload
        init_data = {
            "initializeUploadRequest": {
                "owner": author,
            }
        }
        init_resp = requests.post(
            f"{API_BASE}/images?action=initializeUpload",
            headers=self._headers(),
            json=init_data,
        )
        if init_resp.status_code not in (200, 201):
            return {"error": f"Image init failed: {init_resp.status_code}", "detail": init_resp.text}

        init_result = init_resp.json().get("value", {})
        upload_url = init_result.get("uploadUrl", "")
        image_urn = init_result.get("image", "")

        # Step 2: Upload image binary
        if image_path and os.path.isfile(image_path):
            with open(image_path, "rb") as f:
                img_data = f.read()
        elif image_url:
            dl = requests.get(image_url)
            img_data = dl.content
        else:
            return {"error": "Could not read image"}

        upload_headers = {"Authorization": f"Bearer {self.access_token}"}
        upload_resp = requests.put(upload_url, headers=upload_headers, data=img_data)
        if upload_resp.status_code not in (200, 201):
            return {"error": f"Image upload failed: {upload_resp.status_code}"}

        # Step 3: Create post with image
        post_data = {
            "author": author,
            "commentary": text,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "media": {
                    "title": title or "Image",
                    "id": image_urn,
                }
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        resp = requests.post(f"{API_BASE}/posts", headers=self._headers(), json=post_data)
        if resp.status_code in (200, 201):
            return {"success": True, "post_id": resp.headers.get("x-restli-id", "")}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.text}

    def post_article(
        self,
        text: str,
        article_url: str = "",
        title: str = "",
        description: str = "",
        as_org: bool = False,
    ) -> Dict[str, Any]:
        """Post a link/article to LinkedIn.

        Args:
            text: Post commentary.
            article_url: URL of the article.
            title: Article title.
            description: Article description.
            as_org: Post as organization.
        """
        if not text:
            return {"error": "text is required"}
        if not article_url:
            return {"error": "article_url is required"}
        if not self.access_token:
            return {"error": "LINKEDIN_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        data = {
            "author": self._author_urn(as_org),
            "commentary": text,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "article": {
                    "source": article_url,
                    "title": title,
                    "description": description,
                }
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        resp = requests.post(f"{API_BASE}/posts", headers=self._headers(), json=data)
        if resp.status_code in (200, 201):
            return {"success": True, "post_id": resp.headers.get("x-restli-id", "")}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.text}

    def get_profile(self) -> Dict[str, Any]:
        """Get the authenticated user's LinkedIn profile."""
        if not self.access_token:
            return {"error": "LINKEDIN_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        resp = requests.get(f"{API_BASE}/me", headers=self._headers())
        if resp.status_code == 200:
            return {"success": True, "profile": resp.json()}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.text}

    def delete_post(self, post_urn: str) -> Dict[str, Any]:
        """Delete a LinkedIn post.

        Args:
            post_urn: Full post URN (e.g. urn:li:share:12345).
        """
        if not post_urn:
            return {"error": "post_urn is required"}
        if not self.access_token:
            return {"error": "LINKEDIN_ACCESS_TOKEN required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        resp = requests.delete(
            f"{API_BASE}/posts/{post_urn}",
            headers=self._headers(),
        )
        if resp.status_code in (200, 204):
            return {"success": True}
        return {"error": f"HTTP {resp.status_code}", "detail": resp.text}


# Standalone functions for agent discoverability
def linkedin_post_text(
    text: str,
    visibility: str = "PUBLIC",
    as_org: bool = False,
    access_token: Optional[str] = None,
    person_urn: Optional[str] = None,
) -> Dict[str, Any]:
    """Post a text update to LinkedIn.

    Args:
        text: Post content (max 3000 chars).
        visibility: 'PUBLIC' or 'CONNECTIONS'.
        as_org: Post as organization instead of person.
        access_token: OAuth token (or set LINKEDIN_ACCESS_TOKEN env var).
        person_urn: Person URN (or set LINKEDIN_PERSON_URN env var).
    """
    return LinkedInTool(access_token=access_token, person_urn=person_urn).post_text(
        text=text, visibility=visibility, as_org=as_org
    )


def linkedin_post_image(
    text: str,
    image_url: str = "",
    image_path: str = "",
    title: str = "",
    as_org: bool = False,
    access_token: Optional[str] = None,
    person_urn: Optional[str] = None,
) -> Dict[str, Any]:
    """Post with an image to LinkedIn.

    Args:
        text: Post text.
        image_url: Public URL of image.
        image_path: Local file path to upload.
        title: Image title.
        as_org: Post as organization.
        access_token: OAuth token (or set LINKEDIN_ACCESS_TOKEN env var).
        person_urn: Person URN (or set LINKEDIN_PERSON_URN env var).
    """
    return LinkedInTool(access_token=access_token, person_urn=person_urn).post_image(
        text=text, image_url=image_url, image_path=image_path, title=title, as_org=as_org
    )


def linkedin_post_article(
    text: str,
    article_url: str = "",
    title: str = "",
    description: str = "",
    as_org: bool = False,
    access_token: Optional[str] = None,
    person_urn: Optional[str] = None,
) -> Dict[str, Any]:
    """Post a link/article to LinkedIn.

    Args:
        text: Post commentary.
        article_url: URL of the article.
        title: Article title.
        description: Article description.
        as_org: Post as organization.
        access_token: OAuth token (or set LINKEDIN_ACCESS_TOKEN env var).
        person_urn: Person URN (or set LINKEDIN_PERSON_URN env var).
    """
    return LinkedInTool(access_token=access_token, person_urn=person_urn).post_article(
        text=text, article_url=article_url, title=title, description=description, as_org=as_org
    )


def linkedin_get_profile(
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Get the authenticated user's LinkedIn profile.

    Args:
        access_token: OAuth token (or set LINKEDIN_ACCESS_TOKEN env var).
    """
    return LinkedInTool(access_token=access_token).get_profile()


def linkedin_delete_post(
    post_urn: str,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete a LinkedIn post.

    Args:
        post_urn: Full post URN (e.g. urn:li:share:12345).
        access_token: OAuth token (or set LINKEDIN_ACCESS_TOKEN env var).
    """
    return LinkedInTool(access_token=access_token).delete_post(post_urn=post_urn)
