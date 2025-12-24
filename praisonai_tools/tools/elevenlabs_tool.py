"""ElevenLabs Tool for PraisonAI Agents.

Text-to-speech using ElevenLabs.

Usage:
    from praisonai_tools import ElevenLabsTool
    
    el = ElevenLabsTool()
    audio = el.speak("Hello world!")

Environment Variables:
    ELEVENLABS_API_KEY: ElevenLabs API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ElevenLabsTool(BaseTool):
    """Tool for ElevenLabs text-to-speech."""
    
    name = "elevenlabs"
    description = "Text-to-speech using ElevenLabs."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "speak",
        text: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "speak":
            return self.speak(text=text, **kwargs)
        elif action == "list_voices":
            return self.list_voices()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def speak(self, text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM", output_path: str = None) -> Dict[str, Any]:
        """Convert text to speech."""
        if not text:
            return {"error": "text is required"}
        if not self.api_key:
            return {"error": "ELEVENLABS_API_KEY required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
            data = {"text": text, "model_id": "eleven_monolingual_v1"}
            
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            
            if resp.status_code != 200:
                return {"error": resp.text}
            
            if output_path:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return {"success": True, "output_path": output_path}
            
            return {"success": True, "audio_bytes": len(resp.content)}
        except Exception as e:
            logger.error(f"ElevenLabs speak error: {e}")
            return {"error": str(e)}
    
    def list_voices(self) -> List[Dict[str, Any]]:
        """List available voices."""
        if not self.api_key:
            return [{"error": "ELEVENLABS_API_KEY required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            headers = {"xi-api-key": self.api_key}
            resp = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers, timeout=10)
            data = resp.json()
            
            voices = []
            for v in data.get("voices", []):
                voices.append({
                    "voice_id": v.get("voice_id"),
                    "name": v.get("name"),
                    "category": v.get("category"),
                })
            return voices
        except Exception as e:
            logger.error(f"ElevenLabs list_voices error: {e}")
            return [{"error": str(e)}]


def elevenlabs_speak(text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> Dict[str, Any]:
    """Speak with ElevenLabs."""
    return ElevenLabsTool().speak(text=text, voice_id=voice_id)
