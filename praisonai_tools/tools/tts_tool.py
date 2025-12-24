"""Text-to-Speech Tool for PraisonAI Agents.

Convert text to speech using various providers (OpenAI, ElevenLabs).

Usage:
    from praisonai_tools import TTSTool
    
    tts = TTSTool()  # Uses OPENAI_API_KEY env var
    
    # Generate speech
    result = tts.speak("Hello, world!", output_path="output.mp3")
    
    # With custom voice
    result = tts.speak("Hello!", voice="nova", output_path="output.mp3")

Environment Variables:
    OPENAI_API_KEY: OpenAI API key (for OpenAI TTS)
    ELEVENLABS_API_KEY: ElevenLabs API key (for ElevenLabs TTS)
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

# OpenAI TTS voices
OPENAI_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
OPENAI_MODELS = ["tts-1", "tts-1-hd"]


class TTSTool(BaseTool):
    """Tool for text-to-speech conversion."""
    
    name = "text_to_speech"
    description = "Convert text to speech audio. Supports multiple voices and output formats."
    
    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: str = "tts-1",
        voice: str = "alloy",
        output_dir: Optional[str] = None,
    ):
        """Initialize TTSTool.
        
        Args:
            provider: TTS provider ("openai" or "elevenlabs")
            api_key: API key (or use env var based on provider)
            model: TTS model
            voice: Default voice
            output_dir: Directory for output files
        """
        self.provider = provider.lower()
        self.model = model
        self.voice = voice
        self.output_dir = output_dir or os.getcwd()
        
        if self.provider == "openai":
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        elif self.provider == "elevenlabs":
            self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        else:
            self.api_key = api_key
        
        self._client = None
        super().__init__()
    
    def run(
        self,
        text: str,
        voice: Optional[str] = None,
        output_path: Optional[str] = None,
        model: Optional[str] = None,
        speed: float = 1.0,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """Generate speech from text.
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (overrides default)
            output_path: Path for output file
            model: Model to use (overrides default)
            speed: Speech speed (0.25 to 4.0)
        """
        return self.speak(
            text=text,
            voice=voice,
            output_path=output_path,
            model=model,
            speed=speed,
        )
    
    def speak(
        self,
        text: str,
        voice: Optional[str] = None,
        output_path: Optional[str] = None,
        model: Optional[str] = None,
        speed: float = 1.0,
        response_format: str = "mp3",
    ) -> Dict[str, Any]:
        """Convert text to speech.
        
        Args:
            text: Text to convert
            voice: Voice to use
            output_path: Output file path
            model: TTS model
            speed: Speech speed (0.25 to 4.0)
            response_format: Output format (mp3, opus, aac, flac)
            
        Returns:
            Dict with output path and metadata
        """
        if not text:
            return {"error": "Text is required"}
        
        if not self.api_key:
            return {"error": f"{self.provider.upper()} API key not configured"}
        
        voice = voice or self.voice
        model = model or self.model
        
        if self.provider == "openai":
            return self._openai_tts(text, voice, output_path, model, speed, response_format)
        elif self.provider == "elevenlabs":
            return self._elevenlabs_tts(text, voice, output_path, model)
        else:
            return {"error": f"Unknown provider: {self.provider}"}
    
    def _openai_tts(
        self,
        text: str,
        voice: str,
        output_path: Optional[str],
        model: str,
        speed: float,
        response_format: str,
    ) -> Dict[str, Any]:
        """Generate speech using OpenAI TTS."""
        try:
            from openai import OpenAI
        except ImportError:
            return {"error": "openai not installed. Install with: pip install openai"}
        
        # Validate voice
        if voice not in OPENAI_VOICES:
            return {"error": f"Invalid voice: {voice}. Use one of: {OPENAI_VOICES}"}
        
        # Validate speed
        speed = max(0.25, min(4.0, speed))
        
        # Generate output path if not provided
        if not output_path:
            import hashlib
            text_hash = hashlib.md5(text[:50].encode()).hexdigest()[:8]
            output_path = os.path.join(self.output_dir, f"speech_{text_hash}.{response_format}")
        
        try:
            client = OpenAI(api_key=self.api_key)
            
            response = client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                speed=speed,
                response_format=response_format,
            )
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            
            # Save audio
            response.stream_to_file(output_path)
            
            return {
                "success": True,
                "output_path": output_path,
                "voice": voice,
                "model": model,
                "format": response_format,
                "text_length": len(text),
            }
        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")
            return {"error": str(e)}
    
    def _elevenlabs_tts(
        self,
        text: str,
        voice: str,
        output_path: Optional[str],
        model: str,
    ) -> Dict[str, Any]:
        """Generate speech using ElevenLabs."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        # Generate output path if not provided
        if not output_path:
            import hashlib
            text_hash = hashlib.md5(text[:50].encode()).hexdigest()[:8]
            output_path = os.path.join(self.output_dir, f"speech_{text_hash}.mp3")
        
        try:
            # ElevenLabs API
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key,
            }
            
            data = {
                "text": text,
                "model_id": model or "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5,
                },
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=60)
            response.raise_for_status()
            
            # Save audio
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            return {
                "success": True,
                "output_path": output_path,
                "voice": voice,
                "model": model,
                "text_length": len(text),
            }
        except Exception as e:
            logger.error(f"ElevenLabs TTS error: {e}")
            return {"error": str(e)}
    
    def list_voices(self) -> Dict[str, Any]:
        """List available voices for the current provider.
        
        Returns:
            Dict with available voices
        """
        if self.provider == "openai":
            return {
                "provider": "openai",
                "voices": OPENAI_VOICES,
                "models": OPENAI_MODELS,
            }
        elif self.provider == "elevenlabs":
            return self._list_elevenlabs_voices()
        else:
            return {"error": f"Unknown provider: {self.provider}"}
    
    def _list_elevenlabs_voices(self) -> Dict[str, Any]:
        """List ElevenLabs voices."""
        if not self.api_key:
            return {"error": "ELEVENLABS_API_KEY not configured"}
        
        try:
            import requests
            
            url = "https://api.elevenlabs.io/v1/voices"
            headers = {"xi-api-key": self.api_key}
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            voices = [
                {"voice_id": v["voice_id"], "name": v["name"]}
                for v in data.get("voices", [])
            ]
            
            return {"provider": "elevenlabs", "voices": voices}
        except Exception as e:
            return {"error": str(e)}


def text_to_speech(
    text: str,
    voice: str = "alloy",
    output_path: Optional[str] = None,
    provider: str = "openai",
) -> Dict[str, Any]:
    """Convert text to speech."""
    return TTSTool(provider=provider).speak(text=text, voice=voice, output_path=output_path)


def list_tts_voices(provider: str = "openai") -> Dict[str, Any]:
    """List available TTS voices."""
    return TTSTool(provider=provider).list_voices()
