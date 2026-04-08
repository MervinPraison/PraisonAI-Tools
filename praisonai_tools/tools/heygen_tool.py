"""HeyGen Tool for PraisonAI Agents.

AI avatar video generation using HeyGen REST API with full customisation.

Usage:
    from praisonai_tools import HeyGenTool

    heygen = HeyGenTool()

    # List resources
    avatars = heygen.list_avatars()
    groups = heygen.list_avatar_groups()
    voices = heygen.list_voices()

    # Generate video with TTS voice
    video = heygen.generate_video(
        script="Hello world",
        avatar_id="avatar_id",
        voice_id="voice_id",
    )

    # Generate video with external audio (e.g. ElevenLabs)
    asset = heygen.upload_asset("/path/to/audio.mp3")
    video = heygen.generate_video_with_audio(
        avatar_id="avatar_id",
        audio_asset_id=asset["id"],
    )

    # Poll status
    status = heygen.video_status("video_id")

    # Quota check
    quota = heygen.get_remaining_quota()

Environment Variables:
    HEYGEN_API_KEY: HeyGen API key
"""

import os
import time
import logging
from typing import Any, Dict, Optional, Union, List

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class HeyGenTool(BaseTool):
    """Tool for HeyGen AI avatar video generation.

    Supports all HeyGen Studio API v2 features:
    - Avatar listing (all, by group, details)
    - Voice listing and management
    - Video generation with TTS or external audio
    - Asset upload (audio/image/video)
    - Video status polling and management
    - Quota checking
    """

    name = "heygen"
    description = "AI avatar video generation using HeyGen."

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("HEYGEN_API_KEY")
        self.base_url = "https://api.heygen.com"
        self.upload_url = "https://upload.heygen.com"
        super().__init__()

    def _get_headers(self, content_type: str = "application/json") -> Dict[str, str]:
        """Get request headers with API key."""
        if not self.api_key:
            raise ValueError("HEYGEN_API_KEY required")
        headers = {"x-api-key": self.api_key, "accept": "application/json"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. pip install requests"}

        try:
            resp = requests.request(method, url, **kwargs)
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}
            if resp.status_code not in (200, 201):
                return {"error": f"HTTP {resp.status_code}", "detail": data}
            return data
        except Exception as e:
            logger.error(f"HeyGen request error: {e}")
            return {"error": str(e)}

    def run(
        self,
        action: str = "generate_video",
        **kwargs,
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        """Run a HeyGen action.

        Actions:
            list_avatars, list_avatar_groups, list_group_avatars,
            get_avatar_details, list_voices, list_voice_locales,
            generate_video, generate_video_with_audio,
            video_status, list_videos, delete_video,
            upload_asset, list_assets, delete_asset,
            get_remaining_quota, get_user_info
        """
        action = action.lower().replace("-", "_")
        handler = getattr(self, action, None)
        if handler and callable(handler) and not action.startswith("_"):
            return handler(**kwargs)
        return {"error": f"Unknown action: {action}"}

    # ─── Avatar Management ────────────────────────────────────────────────

    def list_avatars(self) -> Dict[str, Any]:
        """List all available HeyGen avatars."""
        return self._request(
            "GET",
            f"{self.base_url}/v2/avatars",
            headers=self._get_headers(),
            timeout=30,
        )

    def list_avatar_groups(self) -> Dict[str, Any]:
        """List all avatar groups."""
        return self._request(
            "GET",
            f"{self.base_url}/v2/avatar_group.list",
            headers=self._get_headers(),
            timeout=30,
        )

    def list_group_avatars(self, group_id: str) -> Dict[str, Any]:
        """List all avatars in a specific avatar group.

        Args:
            group_id: The avatar group ID.
        """
        if not group_id:
            return {"error": "group_id is required"}
        return self._request(
            "GET",
            f"{self.base_url}/v2/avatar_group/{group_id}/avatars",
            headers=self._get_headers(),
            timeout=30,
        )

    def get_avatar_details(self, avatar_id: str) -> Dict[str, Any]:
        """Get detailed info about a specific avatar.

        Args:
            avatar_id: The avatar ID.
        """
        if not avatar_id:
            return {"error": "avatar_id is required"}
        return self._request(
            "GET",
            f"{self.base_url}/v2/avatar/{avatar_id}",
            headers=self._get_headers(),
            timeout=30,
        )

    # ─── Voice Management ─────────────────────────────────────────────────

    def list_voices(self) -> Dict[str, Any]:
        """List all available HeyGen voices."""
        return self._request(
            "GET",
            f"{self.base_url}/v2/voices",
            headers=self._get_headers(),
            timeout=30,
        )

    def list_voice_locales(self) -> Dict[str, Any]:
        """List all available voice locales/languages."""
        return self._request(
            "GET",
            f"{self.base_url}/v2/voices/locales",
            headers=self._get_headers(),
            timeout=30,
        )

    # ─── Video Generation ─────────────────────────────────────────────────

    def generate_video(
        self,
        script: str,
        avatar_id: str,
        voice_id: str,
        title: str = "Generated Video",
        width: int = 1920,
        height: int = 1080,
        avatar_style: str = "normal",
        speed: float = 1.0,
        pitch: float = 0,
        background_type: Optional[str] = None,
        background_value: Optional[str] = None,
        background_url: Optional[str] = None,
        callback_url: Optional[str] = None,
        caption: bool = False,
    ) -> Dict[str, Any]:
        """Generate an AI avatar video from text script using HeyGen TTS.

        Args:
            script: Text for the avatar to speak (max 5000 chars).
            avatar_id: Avatar ID (from list_avatars or list_group_avatars).
            voice_id: Voice ID (from list_voices).
            title: Video title.
            width: Video width in pixels.
            height: Video height in pixels.
            avatar_style: Avatar style ('normal', 'circle', 'closeUp').
            speed: Speech speed multiplier (0.5-1.5).
            pitch: Voice pitch adjustment.
            background_type: Background type ('color', 'image', 'video').
            background_value: Background color hex (e.g. '#ffffff').
            background_url: Background image/video URL.
            callback_url: Webhook URL for completion notification.
            caption: Whether to generate captions.
        """
        if not script:
            return {"error": "script is required"}
        if not avatar_id:
            return {"error": "avatar_id is required"}
        if not voice_id:
            return {"error": "voice_id is required"}
        if len(script) > 5000:
            return {"error": "script exceeds 5000 character limit"}

        voice_config = {
            "type": "text_to_speech",
            "voice_id": voice_id,
            "input_text": script,
            "speed": speed,
            "pitch": pitch,
        }

        return self._generate(
            voice_config=voice_config,
            avatar_id=avatar_id,
            title=title,
            width=width,
            height=height,
            avatar_style=avatar_style,
            background_type=background_type,
            background_value=background_value,
            background_url=background_url,
            callback_url=callback_url,
            caption=caption,
        )

    def generate_video_with_audio(
        self,
        avatar_id: str,
        audio_asset_id: Optional[str] = None,
        audio_url: Optional[str] = None,
        title: str = "Generated Video",
        width: int = 1920,
        height: int = 1080,
        avatar_style: str = "normal",
        background_type: Optional[str] = None,
        background_value: Optional[str] = None,
        background_url: Optional[str] = None,
        callback_url: Optional[str] = None,
        caption: bool = False,
    ) -> Dict[str, Any]:
        """Generate video using external audio (e.g. ElevenLabs, uploaded file).

        Provide either audio_asset_id (from upload_asset) or audio_url, not both.

        Args:
            avatar_id: Avatar ID.
            audio_asset_id: Asset ID from upload_asset().
            audio_url: Public URL to audio file.
            title: Video title.
            width: Video width in pixels.
            height: Video height in pixels.
            avatar_style: Avatar style ('normal', 'circle', 'closeUp').
            background_type: Background type ('color', 'image', 'video').
            background_value: Background color hex.
            background_url: Background image/video URL.
            callback_url: Webhook URL for completion notification.
            caption: Whether to generate captions.
        """
        if not avatar_id:
            return {"error": "avatar_id is required"}
        if not audio_asset_id and not audio_url:
            return {"error": "either audio_asset_id or audio_url is required"}
        if audio_asset_id and audio_url:
            return {"error": "provide only one of audio_asset_id or audio_url"}

        voice_config = {"type": "audio"}
        if audio_asset_id:
            voice_config["audio_asset_id"] = audio_asset_id
        else:
            voice_config["audio_url"] = audio_url

        return self._generate(
            voice_config=voice_config,
            avatar_id=avatar_id,
            title=title,
            width=width,
            height=height,
            avatar_style=avatar_style,
            background_type=background_type,
            background_value=background_value,
            background_url=background_url,
            callback_url=callback_url,
            caption=caption,
        )

    def generate_video_multi_scene(
        self,
        scenes: List[Dict[str, Any]],
        title: str = "Generated Video",
        width: int = 1920,
        height: int = 1080,
        callback_url: Optional[str] = None,
        caption: bool = False,
    ) -> Dict[str, Any]:
        """Generate video with multiple scenes/inputs.

        Args:
            scenes: List of scene dicts, each containing:
                - avatar_id (str): Avatar for this scene.
                - voice_id (str, optional): Voice ID for TTS.
                - script (str, optional): Text script for TTS.
                - audio_asset_id (str, optional): Upload asset ID for audio.
                - audio_url (str, optional): Public audio URL.
                - avatar_style (str, optional): Style override.
                - background_type (str, optional): Background type.
                - background_value (str, optional): Background color.
                - background_url (str, optional): Background media URL.
            title: Video title.
            width: Video width.
            height: Video height.
            callback_url: Webhook URL.
            caption: Generate captions.
        """
        if not scenes:
            return {"error": "scenes list is required"}

        video_inputs = []
        for scene in scenes:
            avatar_id = scene.get("avatar_id")
            if not avatar_id:
                return {"error": "each scene requires avatar_id"}

            character = {
                "type": "avatar",
                "avatar_id": avatar_id,
                "avatar_style": scene.get("avatar_style", "normal"),
            }

            # Voice config
            if scene.get("audio_asset_id") or scene.get("audio_url"):
                voice = {"type": "audio"}
                if scene.get("audio_asset_id"):
                    voice["audio_asset_id"] = scene["audio_asset_id"]
                else:
                    voice["audio_url"] = scene["audio_url"]
            else:
                voice = {
                    "type": "text_to_speech",
                    "voice_id": scene.get("voice_id", ""),
                    "input_text": scene.get("script", ""),
                    "speed": scene.get("speed", 1.0),
                    "pitch": scene.get("pitch", 0),
                }

            video_input = {"character": character, "voice": voice}

            # Background
            bg_type = scene.get("background_type")
            if bg_type:
                bg = {"type": bg_type}
                if bg_type == "color":
                    bg["value"] = scene.get("background_value", "#ffffff")
                elif bg_type in ("image", "video"):
                    bg["url"] = scene.get("background_url", "")
                video_input["background"] = bg

            video_inputs.append(video_input)

        data = {
            "title": title,
            "video_inputs": video_inputs,
            "dimension": {"width": width, "height": height},
        }
        if callback_url:
            data["callback_url"] = callback_url
        if caption:
            data["caption"] = caption

        return self._request(
            "POST",
            f"{self.base_url}/v2/video/generate",
            headers=self._get_headers(),
            json=data,
            timeout=30,
        )

    def _generate(
        self,
        voice_config: Dict[str, Any],
        avatar_id: str,
        title: str,
        width: int,
        height: int,
        avatar_style: str,
        background_type: Optional[str],
        background_value: Optional[str],
        background_url: Optional[str],
        callback_url: Optional[str],
        caption: bool,
    ) -> Dict[str, Any]:
        """Internal: build and send video generation request."""
        character = {
            "type": "avatar",
            "avatar_id": avatar_id,
            "avatar_style": avatar_style,
        }

        video_input = {"character": character, "voice": voice_config}

        # Background
        if background_type:
            bg = {"type": background_type}
            if background_type == "color":
                bg["value"] = background_value or "#ffffff"
            elif background_type in ("image", "video"):
                bg["url"] = background_url or ""
            video_input["background"] = bg

        data = {
            "title": title,
            "video_inputs": [video_input],
            "dimension": {"width": width, "height": height},
        }
        if callback_url:
            data["callback_url"] = callback_url
        if caption:
            data["caption"] = caption

        return self._request(
            "POST",
            f"{self.base_url}/v2/video/generate",
            headers=self._get_headers(),
            json=data,
            timeout=30,
        )

    # ─── Video Status & Management ────────────────────────────────────────

    def video_status(self, video_id: str) -> Dict[str, Any]:
        """Check HeyGen video generation status and return download URL when ready.

        Args:
            video_id: The video ID from generate_video response.
        """
        if not video_id:
            return {"error": "video_id is required"}
        return self._request(
            "GET",
            f"{self.base_url}/v1/video_status.get",
            headers=self._get_headers(),
            params={"video_id": video_id},
            timeout=10,
        )

    def wait_for_video(
        self,
        video_id: str,
        poll_interval: int = 10,
        max_wait: int = 300,
    ) -> Dict[str, Any]:
        """Poll video status until completed or failed.

        Args:
            video_id: The video ID.
            poll_interval: Seconds between status checks.
            max_wait: Maximum seconds to wait.

        Returns:
            Final status dict with video_url if completed.
        """
        if not video_id:
            return {"error": "video_id is required"}

        start = time.time()
        while time.time() - start < max_wait:
            result = self.video_status(video_id)
            data = result.get("data", result)
            status = data.get("status", "unknown")

            if status == "completed":
                return result
            elif status in ("failed", "error"):
                return result

            time.sleep(poll_interval)

        return {"error": f"Timeout after {max_wait}s", "video_id": video_id}

    def list_videos(self) -> Dict[str, Any]:
        """List all videos in the account."""
        return self._request(
            "GET",
            f"{self.base_url}/v1/video.list",
            headers=self._get_headers(),
            timeout=30,
        )

    def delete_video(self, video_id: str) -> Dict[str, Any]:
        """Delete a video.

        Args:
            video_id: The video ID to delete.
        """
        if not video_id:
            return {"error": "video_id is required"}
        return self._request(
            "DELETE",
            f"{self.base_url}/v1/video.delete",
            headers=self._get_headers(),
            json={"video_id": video_id},
            timeout=10,
        )

    # ─── Asset Management ─────────────────────────────────────────────────

    def upload_asset(
        self,
        file_path: Optional[str] = None,
        file_data: Optional[bytes] = None,
        content_type: str = "audio/mpeg",
    ) -> Dict[str, Any]:
        """Upload an asset (audio/image/video) to HeyGen.

        Uses upload.heygen.com with raw binary body.

        Args:
            file_path: Local path to file to upload.
            file_data: Raw bytes to upload (alternative to file_path).
            content_type: MIME type (audio/mpeg, image/png, video/mp4, etc.).

        Returns:
            Dict with 'id' (asset_id) and 'url' fields.
        """
        if not file_path and not file_data:
            return {"error": "file_path or file_data is required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        try:
            if file_path:
                with open(file_path, "rb") as f:
                    file_data = f.read()

            headers = {
                "x-api-key": self.api_key,
                "Content-Type": content_type,
                "accept": "application/json",
            }

            resp = requests.post(
                f"{self.upload_url}/v1/asset",
                headers=headers,
                data=file_data,
                timeout=60,
            )

            try:
                result = resp.json()
            except Exception:
                return {"error": f"Upload failed: {resp.text}"}

            if resp.status_code not in (200, 201):
                return {"error": f"HTTP {resp.status_code}", "detail": result}

            # Normalize response to always have 'id'
            data = result.get("data", result)
            asset_id = data.get("id") or data.get("asset_id")
            url = data.get("url", "")

            return {
                "id": asset_id,
                "url": url,
                "file_type": data.get("file_type", ""),
                "raw": result,
            }
        except Exception as e:
            logger.error(f"HeyGen upload_asset error: {e}")
            return {"error": str(e)}

    def list_assets(self) -> Dict[str, Any]:
        """List all uploaded assets."""
        return self._request(
            "GET",
            f"{self.base_url}/v1/asset",
            headers=self._get_headers(),
            timeout=30,
        )

    def delete_asset(self, asset_id: str) -> Dict[str, Any]:
        """Delete an uploaded asset.

        Args:
            asset_id: The asset ID to delete.
        """
        if not asset_id:
            return {"error": "asset_id is required"}
        return self._request(
            "POST",
            f"{self.base_url}/v1/asset.delete",
            headers=self._get_headers(),
            json={"asset_id": asset_id},
            timeout=10,
        )

    # ─── Account ──────────────────────────────────────────────────────────

    def get_remaining_quota(self) -> Dict[str, Any]:
        """Get remaining API quota/credits."""
        return self._request(
            "GET",
            f"{self.base_url}/v2/user/remaining_quota",
            headers=self._get_headers(),
            timeout=10,
        )

    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information."""
        return self._request(
            "GET",
            f"{self.base_url}/v2/user/me",
            headers=self._get_headers(),
            timeout=10,
        )

    # ─── Templates ────────────────────────────────────────────────────────

    def list_templates(self) -> Dict[str, Any]:
        """List all available templates."""
        return self._request(
            "GET",
            f"{self.base_url}/v2/templates",
            headers=self._get_headers(),
            timeout=30,
        )

    def get_template(self, template_id: str) -> Dict[str, Any]:
        """Get template details.

        Args:
            template_id: The template ID.
        """
        if not template_id:
            return {"error": "template_id is required"}
        return self._request(
            "GET",
            f"{self.base_url}/v2/template/{template_id}",
            headers=self._get_headers(),
            timeout=30,
        )

    def generate_from_template(
        self,
        template_id: str,
        variables: Optional[Dict[str, Any]] = None,
        title: str = "Template Video",
        callback_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a video from a template with variable substitution.

        Args:
            template_id: Template ID.
            variables: Dict of template variable overrides.
            title: Video title.
            callback_url: Webhook URL.
        """
        if not template_id:
            return {"error": "template_id is required"}

        data = {"template_id": template_id, "title": title}
        if variables:
            data["variables"] = variables
        if callback_url:
            data["callback_url"] = callback_url

        return self._request(
            "POST",
            f"{self.base_url}/v2/template/generate",
            headers=self._get_headers(),
            json=data,
            timeout=30,
        )

    # ─── Translate ────────────────────────────────────────────────────────

    def translate_video(
        self,
        video_url: str,
        target_language: str,
        title: str = "Translated Video",
        callback_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Translate a video to another language.

        Args:
            video_url: URL of the source video.
            target_language: Target language code (e.g. 'es', 'fr', 'zh').
            title: Title for translated video.
            callback_url: Webhook URL.
        """
        if not video_url:
            return {"error": "video_url is required"}
        if not target_language:
            return {"error": "target_language is required"}

        data = {
            "video_url": video_url,
            "output_language": target_language,
            "title": title,
        }
        if callback_url:
            data["callback_url"] = callback_url

        return self._request(
            "POST",
            f"{self.base_url}/v2/video_translate",
            headers=self._get_headers(),
            json=data,
            timeout=30,
        )

    def list_supported_languages(self) -> Dict[str, Any]:
        """List supported languages for video translation."""
        return self._request(
            "GET",
            f"{self.base_url}/v2/video_translate/target_languages",
            headers=self._get_headers(),
            timeout=10,
        )


# ─── Standalone Functions ─────────────────────────────────────────────────────
# Each function exposes parameters explicitly for agent discoverability.


def heygen_list_avatars(api_key: Optional[str] = None) -> Dict[str, Any]:
    """List available HeyGen avatars."""
    return HeyGenTool(api_key=api_key).list_avatars()


def heygen_list_avatar_groups(api_key: Optional[str] = None) -> Dict[str, Any]:
    """List all HeyGen avatar groups."""
    return HeyGenTool(api_key=api_key).list_avatar_groups()


def heygen_list_group_avatars(
    group_id: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """List all avatars in a specific avatar group."""
    return HeyGenTool(api_key=api_key).list_group_avatars(group_id)


def heygen_get_avatar_details(
    avatar_id: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get detailed info about a specific avatar."""
    return HeyGenTool(api_key=api_key).get_avatar_details(avatar_id)


def heygen_list_voices(api_key: Optional[str] = None) -> Dict[str, Any]:
    """List available HeyGen voices."""
    return HeyGenTool(api_key=api_key).list_voices()


def heygen_list_voice_locales(api_key: Optional[str] = None) -> Dict[str, Any]:
    """List available voice locales/languages."""
    return HeyGenTool(api_key=api_key).list_voice_locales()


def heygen_generate_video(
    script: str,
    avatar_id: str,
    voice_id: str,
    title: str = "Generated Video",
    width: int = 1920,
    height: int = 1080,
    avatar_style: str = "normal",
    speed: float = 1.0,
    pitch: float = 0,
    background_type: Optional[str] = None,
    background_value: Optional[str] = None,
    background_url: Optional[str] = None,
    callback_url: Optional[str] = None,
    caption: bool = False,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate an AI avatar video from text script using HeyGen TTS."""
    return HeyGenTool(api_key=api_key).generate_video(
        script=script,
        avatar_id=avatar_id,
        voice_id=voice_id,
        title=title,
        width=width,
        height=height,
        avatar_style=avatar_style,
        speed=speed,
        pitch=pitch,
        background_type=background_type,
        background_value=background_value,
        background_url=background_url,
        callback_url=callback_url,
        caption=caption,
    )


def heygen_generate_video_with_audio(
    avatar_id: str,
    audio_asset_id: Optional[str] = None,
    audio_url: Optional[str] = None,
    title: str = "Generated Video",
    width: int = 1920,
    height: int = 1080,
    avatar_style: str = "normal",
    background_type: Optional[str] = None,
    background_value: Optional[str] = None,
    background_url: Optional[str] = None,
    callback_url: Optional[str] = None,
    caption: bool = False,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate video using external audio (e.g. ElevenLabs uploaded file)."""
    return HeyGenTool(api_key=api_key).generate_video_with_audio(
        avatar_id=avatar_id,
        audio_asset_id=audio_asset_id,
        audio_url=audio_url,
        title=title,
        width=width,
        height=height,
        avatar_style=avatar_style,
        background_type=background_type,
        background_value=background_value,
        background_url=background_url,
        callback_url=callback_url,
        caption=caption,
    )


def heygen_upload_asset(
    file_path: Optional[str] = None,
    file_data: Optional[bytes] = None,
    content_type: str = "audio/mpeg",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Upload an asset (audio/image/video) to HeyGen."""
    return HeyGenTool(api_key=api_key).upload_asset(
        file_path=file_path,
        file_data=file_data,
        content_type=content_type,
    )


def heygen_video_status(
    video_id: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Check HeyGen video generation status and return download URL when ready."""
    return HeyGenTool(api_key=api_key).video_status(video_id)


def heygen_wait_for_video(
    video_id: str,
    poll_interval: int = 10,
    max_wait: int = 300,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Poll video status until completed or failed."""
    return HeyGenTool(api_key=api_key).wait_for_video(
        video_id=video_id,
        poll_interval=poll_interval,
        max_wait=max_wait,
    )


def heygen_list_videos(api_key: Optional[str] = None) -> Dict[str, Any]:
    """List all videos in the HeyGen account."""
    return HeyGenTool(api_key=api_key).list_videos()


def heygen_delete_video(
    video_id: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete a HeyGen video."""
    return HeyGenTool(api_key=api_key).delete_video(video_id)


def heygen_list_assets(api_key: Optional[str] = None) -> Dict[str, Any]:
    """List all uploaded HeyGen assets."""
    return HeyGenTool(api_key=api_key).list_assets()


def heygen_delete_asset(
    asset_id: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete an uploaded HeyGen asset."""
    return HeyGenTool(api_key=api_key).delete_asset(asset_id)


def heygen_get_remaining_quota(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Get remaining HeyGen API quota/credits."""
    return HeyGenTool(api_key=api_key).get_remaining_quota()


def heygen_get_user_info(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Get current HeyGen user information."""
    return HeyGenTool(api_key=api_key).get_user_info()


def heygen_list_templates(api_key: Optional[str] = None) -> Dict[str, Any]:
    """List all available HeyGen templates."""
    return HeyGenTool(api_key=api_key).list_templates()


def heygen_generate_from_template(
    template_id: str,
    variables: Optional[Dict[str, Any]] = None,
    title: str = "Template Video",
    callback_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a video from a HeyGen template."""
    return HeyGenTool(api_key=api_key).generate_from_template(
        template_id=template_id,
        variables=variables,
        title=title,
        callback_url=callback_url,
    )


def heygen_translate_video(
    video_url: str,
    target_language: str,
    title: str = "Translated Video",
    callback_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Translate a video to another language."""
    return HeyGenTool(api_key=api_key).translate_video(
        video_url=video_url,
        target_language=target_language,
        title=title,
        callback_url=callback_url,
    )