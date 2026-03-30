"""HeyGen Tool for PraisonAI Agents.

AI avatar video generation using HeyGen REST API.

Usage:
    from praisonai_tools import HeyGenTool
    
    heygen = HeyGenTool()
    avatars = heygen.list_avatars()
    voices = heygen.list_voices()
    video = heygen.generate_video("Hello world", "avatar_id", "voice_id")

Environment Variables:
    HEYGEN_API_KEY: HeyGen API key
"""

import os
import logging
from typing import Any, Dict, Optional, Union, List

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class HeyGenTool(BaseTool):
    """Tool for HeyGen AI avatar video generation."""
    
    name = "heygen"
    description = "AI avatar video generation using HeyGen."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("HEYGEN_API_KEY")
        self.base_url = "https://api.heygen.com"
        super().__init__()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key."""
        if not self.api_key:
            raise ValueError("HEYGEN_API_KEY required")
        return {"x-api-key": self.api_key, "Content-Type": "application/json"}
    
    def run(
        self,
        action: str = "generate_video",
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        if action == "list_avatars":
            return self.list_avatars()
        elif action == "list_voices":
            return self.list_voices()
        elif action == "generate_video":
            return self.generate_video(**kwargs)
        elif action == "video_status":
            return self.video_status(kwargs.get("video_id"))
        return {"error": f"Unknown action: {action}"}
    
    def list_avatars(self) -> List[Dict[str, Any]]:
        """List available HeyGen avatars."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = self._get_headers()
            resp = requests.get(
                f"{self.base_url}/v2/avatars",
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"HeyGen list_avatars error: {e}")
            return {"error": str(e)}
    
    def list_voices(self) -> List[Dict[str, Any]]:
        """List available HeyGen voices."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = self._get_headers()
            resp = requests.get(
                f"{self.base_url}/v2/voices",
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"HeyGen list_voices error: {e}")
            return {"error": str(e)}
    
    def generate_video(
        self,
        script: str,
        avatar_id: str,
        voice_id: str,
        title: str = "Generated Video",
        width: int = 1920,
        height: int = 1080,
        use_avatar_iv_model: bool = True
    ) -> Dict[str, Any]:
        """Generate an AI avatar video from text script using HeyGen."""
        if not script:
            return {"error": "script is required"}
        if not avatar_id:
            return {"error": "avatar_id is required"}
        if not voice_id:
            return {"error": "voice_id is required"}
        if len(script) > 5000:
            return {"error": "script exceeds 5000 character limit"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = self._get_headers()
            data = {
                "title": title,
                "video_inputs": [{
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "use_avatar_iv_model": use_avatar_iv_model
                    },
                    "voice": {
                        "type": "text_to_speech",
                        "voice_id": voice_id,
                        "input_text": script
                    }
                }],
                "dimension": {
                    "width": width,
                    "height": height
                }
            }
            
            resp = requests.post(
                f"{self.base_url}/v2/video/generate",
                headers=headers,
                json=data,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"HeyGen generate_video error: {e}")
            return {"error": str(e)}
    
    def video_status(self, video_id: str) -> Dict[str, Any]:
        """Check HeyGen video generation status and return download URL when ready."""
        if not video_id:
            return {"error": "video_id is required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = self._get_headers()
            resp = requests.get(
                f"{self.base_url}/v1/video_status.get",
                headers=headers,
                params={"video_id": video_id},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"HeyGen video_status error: {e}")
            return {"error": str(e)}


def heygen_list_avatars(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available HeyGen avatars."""
    return HeyGenTool(api_key=api_key).list_avatars()


def heygen_list_voices(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available HeyGen voices."""
    return HeyGenTool(api_key=api_key).list_voices()


def heygen_generate_video(
    script: str,
    avatar_id: str,
    voice_id: str,
    title: str = "Generated Video",
    width: int = 1920,
    height: int = 1080,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Generate an AI avatar video from text script using HeyGen."""
    return HeyGenTool(api_key=api_key).generate_video(
        script=script,
        avatar_id=avatar_id,
        voice_id=voice_id,
        title=title,
        width=width,
        height=height
    )


def heygen_video_status(video_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Check HeyGen video generation status and return download URL when ready."""
    return HeyGenTool(api_key=api_key).video_status(video_id)