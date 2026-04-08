"""ElevenLabs Tool for PraisonAI Agents.

Text-to-speech using ElevenLabs with full customisation.

Usage:
    from praisonai_tools import ElevenLabsTool

    el = ElevenLabsTool()

    # List voices
    voices = el.list_voices()

    # Generate speech (use voice_id from list_voices)
    result = el.speak("Hello world!", voice_id="your_voice_id")

    # Save to file
    result = el.speak("Hello!", output_path="/tmp/speech.mp3")

    # Full control
    result = el.speak(
        text="Hello!",
        voice_id="your_voice_id",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
        stability=0.5,
        similarity_boost=0.75,
        style=0.0,
        use_speaker_boost=True,
        output_path="/tmp/speech.mp3",
    )

Environment Variables:
    ELEVENLABS_API_KEY: ElevenLabs API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ElevenLabsTool(BaseTool):
    """Tool for ElevenLabs text-to-speech with full customisation.

    Supports:
    - Text-to-speech with any voice, model, and output format
    - Voice settings (stability, similarity_boost, style, speaker boost)
    - Voice listing and search
    - Voice details
    - Model listing
    - Speech history
    """

    name = "elevenlabs"
    description = "Text-to-speech using ElevenLabs."
    BASE_URL = "https://api.elevenlabs.io"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        super().__init__()

    def _get_headers(self, content_type: str = "application/json") -> Dict[str, str]:
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY required")
        headers = {"xi-api-key": self.api_key, "accept": "application/json"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def run(
        self,
        action: str = "speak",
        text: Optional[str] = None,
        **kwargs,
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        """Run an ElevenLabs action.

        Actions:
            speak, list_voices, get_voice, list_models, get_history
        """
        action = action.lower().replace("-", "_")
        if action == "speak":
            return self.speak(text=text, **kwargs)
        handler = getattr(self, action, None)
        if handler and callable(handler) and not action.startswith("_"):
            return handler(**kwargs)
        return {"error": f"Unknown action: {action}"}

    def speak(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model_id: str = "eleven_multilingual_v2",
        output_format: str = "mp3_44100_128",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
        speed: float = 1.0,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert text to speech with full control.

        Args:
            text: Text to speak.
            voice_id: ElevenLabs voice ID.
            model_id: Model ID (eleven_monolingual_v1, eleven_multilingual_v2,
                       eleven_turbo_v2, eleven_turbo_v2_5, eleven_flash_v2,
                       eleven_flash_v2_5).
            output_format: Audio format (mp3_22050_32, mp3_44100_64,
                           mp3_44100_96, mp3_44100_128, mp3_44100_192,
                           pcm_16000, pcm_22050, pcm_24000, pcm_44100,
                           ulaw_8000).
            stability: Voice stability (0.0-1.0). Lower = more expressive.
            similarity_boost: Voice similarity (0.0-1.0). Higher = closer to
                              original voice.
            style: Style exaggeration (0.0-1.0). Higher = more stylised.
                   Only for v2 models.
            use_speaker_boost: Enhance speaker similarity. Increases latency.
            speed: Speech speed multiplier (0.25-4.0).
            output_path: Path to save audio file. If None, returns bytes length.

        Returns:
            Dict with success status, output_path (if saved), audio_bytes count.
        """
        if not text:
            return {"error": "text is required"}

        # LLMs via function calling may pass empty strings — fall back to defaults
        voice_id = voice_id or "21m00Tcm4TlvDq8ikWAM"
        model_id = model_id or "eleven_multilingual_v2"
        output_format = output_format or "mp3_44100_128"
        stability = stability if stability else 0.5
        similarity_boost = similarity_boost if similarity_boost else 0.75
        speed = speed if speed else 1.0
        if not self.api_key:
            return {"error": "ELEVENLABS_API_KEY required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. pip install requests"}

        try:
            url = f"{self.BASE_URL}/v1/text-to-speech/{voice_id}"
            params = {}
            if output_format != "mp3_44100_128":
                params["output_format"] = output_format

            headers = self._get_headers()
            data = {
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": style,
                    "use_speaker_boost": use_speaker_boost,
                },
            }
            if speed != 1.0:
                data["voice_settings"]["speed"] = speed

            resp = requests.post(
                url,
                headers=headers,
                json=data,
                params=params if params else None,
                timeout=60,
            )

            if resp.status_code != 200:
                try:
                    err = resp.json()
                except Exception:
                    err = resp.text
                return {"error": f"HTTP {resp.status_code}", "detail": err}

            audio_bytes = resp.content

            if output_path:
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(audio_bytes)
                return {
                    "success": True,
                    "output_path": output_path,
                    "audio_bytes": len(audio_bytes),
                    "format": output_format,
                }

            return {
                "success": True,
                "audio_bytes": len(audio_bytes),
                "format": output_format,
                "data": audio_bytes,
            }
        except Exception as e:
            logger.error(f"ElevenLabs speak error: {e}")
            return {"error": str(e)}

    def speak_to_file(
        self,
        text: str,
        output_path: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model_id: str = "eleven_multilingual_v2",
        output_format: str = "mp3_44100_128",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
        speed: float = 1.0,
    ) -> Dict[str, Any]:
        """Convert text to speech and save to file (convenience method).

        Same as speak() but output_path is required.
        """
        return self.speak(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            output_format=output_format,
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            use_speaker_boost=use_speaker_boost,
            speed=speed,
            output_path=output_path,
        )

    def list_voices(self) -> List[Dict[str, Any]]:
        """List all available voices with details."""
        if not self.api_key:
            return [{"error": "ELEVENLABS_API_KEY required"}]

        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]

        try:
            headers = {"xi-api-key": self.api_key}
            resp = requests.get(
                f"{self.BASE_URL}/v1/voices",
                headers=headers,
                timeout=10,
            )
            data = resp.json()

            voices = []
            for v in data.get("voices", []):
                voices.append({
                    "voice_id": v.get("voice_id"),
                    "name": v.get("name"),
                    "category": v.get("category"),
                    "labels": v.get("labels", {}),
                    "description": v.get("description", ""),
                    "preview_url": v.get("preview_url", ""),
                    "available_for_tiers": v.get("available_for_tiers", []),
                })
            return voices
        except Exception as e:
            logger.error(f"ElevenLabs list_voices error: {e}")
            return [{"error": str(e)}]

    def get_voice(self, voice_id: str) -> Dict[str, Any]:
        """Get details about a specific voice.

        Args:
            voice_id: The voice ID.
        """
        if not voice_id:
            return {"error": "voice_id is required"}
        if not self.api_key:
            return {"error": "ELEVENLABS_API_KEY required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        try:
            resp = requests.get(
                f"{self.BASE_URL}/v1/voices/{voice_id}",
                headers={"xi-api-key": self.api_key},
                timeout=10,
            )
            return resp.json()
        except Exception as e:
            logger.error(f"ElevenLabs get_voice error: {e}")
            return {"error": str(e)}

    def list_models(self) -> List[Dict[str, Any]]:
        """List all available TTS models."""
        if not self.api_key:
            return [{"error": "ELEVENLABS_API_KEY required"}]

        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]

        try:
            resp = requests.get(
                f"{self.BASE_URL}/v1/models",
                headers={"xi-api-key": self.api_key},
                timeout=10,
            )
            return resp.json()
        except Exception as e:
            logger.error(f"ElevenLabs list_models error: {e}")
            return [{"error": str(e)}]

    def get_history(self, page_size: int = 20) -> Dict[str, Any]:
        """Get speech generation history.

        Args:
            page_size: Number of items per page (default 20).
        """
        if not self.api_key:
            return {"error": "ELEVENLABS_API_KEY required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        try:
            resp = requests.get(
                f"{self.BASE_URL}/v1/history",
                headers={"xi-api-key": self.api_key},
                params={"page_size": page_size},
                timeout=10,
            )
            return resp.json()
        except Exception as e:
            logger.error(f"ElevenLabs get_history error: {e}")
            return {"error": str(e)}

    def get_user_info(self) -> Dict[str, Any]:
        """Get current user/subscription info."""
        if not self.api_key:
            return {"error": "ELEVENLABS_API_KEY required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        try:
            resp = requests.get(
                f"{self.BASE_URL}/v1/user",
                headers={"xi-api-key": self.api_key},
                timeout=10,
            )
            return resp.json()
        except Exception as e:
            logger.error(f"ElevenLabs get_user_info error: {e}")
            return {"error": str(e)}


# ─── Standalone Functions ─────────────────────────────────────────────────────


def elevenlabs_speak(
    text: str,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",
    model_id: str = "eleven_multilingual_v2",
    output_format: str = "mp3_44100_128",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    use_speaker_boost: bool = True,
    speed: float = 1.0,
    output_path: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert text to speech using ElevenLabs."""
    return ElevenLabsTool(api_key=api_key).speak(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format=output_format,
        stability=stability,
        similarity_boost=similarity_boost,
        style=style,
        use_speaker_boost=use_speaker_boost,
        speed=speed,
        output_path=output_path,
    )


def elevenlabs_speak_to_file(
    text: str,
    output_path: str,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",
    model_id: str = "eleven_multilingual_v2",
    output_format: str = "mp3_44100_128",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    use_speaker_boost: bool = True,
    speed: float = 1.0,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert text to speech and save to file."""
    return ElevenLabsTool(api_key=api_key).speak_to_file(
        text=text,
        output_path=output_path,
        voice_id=voice_id,
        model_id=model_id,
        output_format=output_format,
        stability=stability,
        similarity_boost=similarity_boost,
        style=style,
        use_speaker_boost=use_speaker_boost,
        speed=speed,
    )


def elevenlabs_list_voices(
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List available ElevenLabs voices."""
    return ElevenLabsTool(api_key=api_key).list_voices()


def elevenlabs_get_voice(
    voice_id: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get details about a specific ElevenLabs voice."""
    return ElevenLabsTool(api_key=api_key).get_voice(voice_id)


def elevenlabs_list_models(
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List available ElevenLabs TTS models."""
    return ElevenLabsTool(api_key=api_key).list_models()


def elevenlabs_get_history(
    page_size: int = 20,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get ElevenLabs speech generation history."""
    return ElevenLabsTool(api_key=api_key).get_history(page_size=page_size)


def elevenlabs_get_user_info(
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get ElevenLabs user/subscription info."""
    return ElevenLabsTool(api_key=api_key).get_user_info()
