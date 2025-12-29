"""
Whisper Tool - Audio transcription via OpenAI Whisper API.

Provides:
- Transcribing audio files
- Word-level timestamps
- Multiple output formats (txt, srt, vtt, json)
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

import sys
import os as _os
_dir = _os.path.dirname(_os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

try:
    from .base import RecipeToolBase
except ImportError:
    from base import RecipeToolBase

logger = logging.getLogger(__name__)


@dataclass
class WordTimestamp:
    """Word with timestamp."""
    word: str
    start: float
    end: float


@dataclass
class TranscriptSegment:
    """Segment of transcript."""
    id: int
    start: float
    end: float
    text: str
    words: List[WordTimestamp] = field(default_factory=list)


@dataclass
class TranscriptResult:
    """Result of transcription."""
    path: str
    text: str
    language: str
    duration: float
    segments: List[TranscriptSegment] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "text": self.text,
            "language": self.language,
            "duration": self.duration,
            "segment_count": len(self.segments),
        }
    
    def to_srt(self) -> str:
        """Convert to SRT format."""
        lines = []
        for i, seg in enumerate(self.segments, 1):
            start = self._format_timestamp_srt(seg.start)
            end = self._format_timestamp_srt(seg.end)
            lines.append(f"{i}")
            lines.append(f"{start} --> {end}")
            lines.append(seg.text.strip())
            lines.append("")
        return "\n".join(lines)
    
    def to_vtt(self) -> str:
        """Convert to VTT format."""
        lines = ["WEBVTT", ""]
        for seg in self.segments:
            start = self._format_timestamp_vtt(seg.start)
            end = self._format_timestamp_vtt(seg.end)
            lines.append(f"{start} --> {end}")
            lines.append(seg.text.strip())
            lines.append("")
        return "\n".join(lines)
    
    def _format_timestamp_srt(self, seconds: float) -> str:
        """Format timestamp for SRT (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_timestamp_vtt(self, seconds: float) -> str:
        """Format timestamp for VTT (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


class WhisperTool(RecipeToolBase):
    """
    Audio transcription tool using OpenAI Whisper API.
    
    Provides transcription with word-level timestamps.
    """
    
    name = "whisper_tool"
    description = "Audio transcription via OpenAI Whisper API"
    
    def __init__(
        self,
        verbose: bool = False,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "whisper-1",
    ):
        super().__init__(verbose)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model
        self._client = None
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check for OpenAI API key."""
        has_key = bool(self.api_key)
        return {
            "openai_api_key": has_key,
            "openai": self._check_openai_package(),
        }
    
    def _check_openai_package(self) -> bool:
        """Check if openai package is available."""
        import importlib.util
        return importlib.util.find_spec("openai") is not None
    
    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                    "or pass api_key parameter."
                )
            
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        
        return self._client
    
    def transcribe(
        self,
        path: Union[str, Path],
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        response_format: str = "verbose_json",
        timestamp_granularities: Optional[List[str]] = None,
    ) -> TranscriptResult:
        """
        Transcribe an audio file.
        
        Args:
            path: Path to audio file
            language: Language code (e.g., "en", "es")
            prompt: Optional prompt to guide transcription
            response_format: Response format (json, text, srt, vtt, verbose_json)
            timestamp_granularities: Timestamp detail level (word, segment)
            
        Returns:
            TranscriptResult with transcription
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")
        
        client = self._get_client()
        
        # Default to word-level timestamps
        if timestamp_granularities is None:
            timestamp_granularities = ["word", "segment"]
        
        # Open and transcribe
        with open(path, "rb") as audio_file:
            kwargs = {
                "model": self.model,
                "file": audio_file,
                "response_format": response_format,
            }
            
            if language:
                kwargs["language"] = language
            if prompt:
                kwargs["prompt"] = prompt
            if response_format == "verbose_json":
                kwargs["timestamp_granularities"] = timestamp_granularities
            
            response = client.audio.transcriptions.create(**kwargs)
        
        # Parse response
        if response_format == "verbose_json":
            return self._parse_verbose_response(path, response)
        elif response_format == "json":
            return TranscriptResult(
                path=str(path),
                text=response.text,
                language=getattr(response, "language", "unknown"),
                duration=getattr(response, "duration", 0),
            )
        else:
            # text, srt, vtt - response is a string
            return TranscriptResult(
                path=str(path),
                text=str(response),
                language="unknown",
                duration=0,
            )
    
    def _parse_verbose_response(self, path: Path, response) -> TranscriptResult:
        """Parse verbose JSON response."""
        segments = []
        
        for i, seg in enumerate(getattr(response, "segments", [])):
            words = []
            for w in getattr(seg, "words", []):
                words.append(WordTimestamp(
                    word=w.word,
                    start=w.start,
                    end=w.end,
                ))
            
            segments.append(TranscriptSegment(
                id=i,
                start=seg.start,
                end=seg.end,
                text=seg.text,
                words=words,
            ))
        
        return TranscriptResult(
            path=str(path),
            text=response.text,
            language=getattr(response, "language", "unknown"),
            duration=getattr(response, "duration", 0),
            segments=segments,
        )
    
    def transcribe_to_file(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        format: str = "txt",
        language: Optional[str] = None,
    ) -> Path:
        """
        Transcribe audio and save to file.
        
        Args:
            input_path: Input audio file
            output_path: Output file path
            format: Output format (txt, srt, vtt, json)
            language: Language code
            
        Returns:
            Path to output file
        """
        input_path = Path(input_path)
        
        if output_path is None:
            output_path = self._generate_output_path(input_path, extension=format)
        else:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
        
        # Transcribe
        result = self.transcribe(input_path, language=language)
        
        # Write output
        if format == "txt":
            output_path.write_text(result.text, encoding="utf-8")
        elif format == "srt":
            output_path.write_text(result.to_srt(), encoding="utf-8")
        elif format == "vtt":
            output_path.write_text(result.to_vtt(), encoding="utf-8")
        elif format == "json":
            output_path.write_text(
                json.dumps(result.to_dict(), indent=2),
                encoding="utf-8"
            )
        else:
            raise ValueError(f"Unknown format: {format}")
        
        return output_path
    
    def detect_language(self, path: Union[str, Path]) -> str:
        """
        Detect language of audio file.
        
        Args:
            path: Path to audio file
            
        Returns:
            Language code
        """
        result = self.transcribe(path)
        return result.language


# Convenience functions
def whisper_transcribe(
    path: Union[str, Path],
    language: Optional[str] = None,
    api_key: Optional[str] = None,
    verbose: bool = False,
) -> TranscriptResult:
    """Transcribe an audio file."""
    return WhisperTool(verbose=verbose, api_key=api_key).transcribe(path, language)
