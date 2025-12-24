"""Cartesia Tool for PraisonAI Agents.

Text-to-speech using Cartesia.

Usage:
    from praisonai_tools import CartesiaTool
    
    cartesia = CartesiaTool()
    audio = cartesia.speak("Hello world!")

Environment Variables:
    CARTESIA_API_KEY: Cartesia API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class CartesiaTool(BaseTool):
    """Tool for Cartesia text-to-speech."""
    
    name = "cartesia"
    description = "Text-to-speech using Cartesia."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CARTESIA_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "speak",
        text: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        if action == "speak":
            return self.speak(text=text, **kwargs)
        elif action == "list_voices":
            return self.list_voices()
        return {"error": f"Unknown action: {action}"}
    
    def speak(self, text: str, voice_id: str = None, output_path: str = None) -> Dict[str, Any]:
        """Convert text to speech."""
        if not text:
            return {"error": "text is required"}
        if not self.api_key:
            return {"error": "CARTESIA_API_KEY required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
            data = {
                "transcript": text,
                "voice": {"mode": "id", "id": voice_id or "a0e99841-438c-4a64-b679-ae501e7d6091"},
                "output_format": {"container": "mp3", "encoding": "mp3", "sample_rate": 44100},
            }
            resp = requests.post(
                "https://api.cartesia.ai/tts/bytes",
                headers=headers,
                json=data,
                timeout=30,
            )
            
            if resp.status_code != 200:
                return {"error": resp.text}
            
            if output_path:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return {"success": True, "output_path": output_path}
            return {"success": True, "audio_bytes": len(resp.content)}
        except Exception as e:
            logger.error(f"Cartesia speak error: {e}")
            return {"error": str(e)}
    
    def list_voices(self) -> List[Dict[str, Any]]:
        """List available voices."""
        if not self.api_key:
            return [{"error": "CARTESIA_API_KEY required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            headers = {"X-API-Key": self.api_key}
            resp = requests.get("https://api.cartesia.ai/voices", headers=headers, timeout=10)
            return resp.json()
        except Exception as e:
            logger.error(f"Cartesia list_voices error: {e}")
            return [{"error": str(e)}]


def cartesia_speak(text: str) -> Dict[str, Any]:
    """Speak with Cartesia."""
    return CartesiaTool().speak(text=text)
