"""Audio transcription with word-level timestamps."""

import os
import subprocess
import tempfile
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class Word:
    """A word with timing information."""
    text: str
    start: float
    end: float
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
        }


@dataclass
class TranscriptResult:
    """Result of transcription."""
    text: str
    words: List[Word] = field(default_factory=list)
    language: str = "en"
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "words": [w.to_dict() for w in self.words],
            "language": self.language,
            "duration": self.duration,
        }
    
    def to_srt(self) -> str:
        """Convert to SRT subtitle format."""
        if not self.words:
            return ""
        
        lines = []
        idx = 1
        
        # Group words into segments of ~5-7 words or by sentence boundaries
        segment_words = []
        for word in self.words:
            segment_words.append(word)
            # Break on punctuation or every 7 words
            if (word.text.rstrip().endswith(('.', '!', '?', ',')) or 
                len(segment_words) >= 7):
                if segment_words:
                    start = segment_words[0].start
                    end = segment_words[-1].end
                    text = " ".join(w.text for w in segment_words)
                    lines.append(f"{idx}")
                    lines.append(f"{_format_srt_time(start)} --> {_format_srt_time(end)}")
                    lines.append(text.strip())
                    lines.append("")
                    idx += 1
                    segment_words = []
        
        # Handle remaining words
        if segment_words:
            start = segment_words[0].start
            end = segment_words[-1].end
            text = " ".join(w.text for w in segment_words)
            lines.append(f"{idx}")
            lines.append(f"{_format_srt_time(start)} --> {_format_srt_time(end)}")
            lines.append(text.strip())
            lines.append("")
        
        return "\n".join(lines)


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _find_ffmpeg() -> str:
    """Find ffmpeg executable."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    
    common_paths = [
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/usr/bin/ffmpeg",
    ]
    for path in common_paths:
        if Path(path).exists():
            return path
    
    raise FileNotFoundError("ffmpeg not found")


def _extract_audio(video_path: str, output_path: str) -> None:
    """Extract audio from video file."""
    ffmpeg = _find_ffmpeg()
    cmd = [
        ffmpeg, "-y",
        "-i", video_path,
        "-vn",  # No video
        "-acodec", "pcm_s16le",
        "-ar", "16000",  # 16kHz for Whisper
        "-ac", "1",  # Mono
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def transcribe_video(
    video_path: str,
    use_local: bool = False,
    model: str = "whisper-1",
    language: Optional[str] = None,
) -> TranscriptResult:
    """
    Transcribe audio from a video file.
    
    Args:
        video_path: Path to the video file
        use_local: If True, use local faster-whisper instead of OpenAI API
        model: Model to use (whisper-1 for OpenAI, or local model name)
        language: Optional language code (e.g., "en")
        
    Returns:
        TranscriptResult with full text and word-level timestamps
        
    Raises:
        FileNotFoundError: If video file not found
        RuntimeError: If transcription fails
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Extract audio to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = tmp.name
    
    try:
        _extract_audio(str(path), audio_path)
        
        if use_local:
            return _transcribe_local(audio_path, model, language)
        else:
            return _transcribe_openai(audio_path, model, language)
    finally:
        # Clean up temp file
        if os.path.exists(audio_path):
            os.unlink(audio_path)


def _transcribe_openai(
    audio_path: str,
    model: str = "whisper-1",
    language: Optional[str] = None,
) -> TranscriptResult:
    """Transcribe using OpenAI Whisper API."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package required: pip install openai")
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable required")
    
    client = OpenAI(api_key=api_key)
    
    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model=model,
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["word"],
            language=language,
        )
    
    # Parse response
    words = []
    if hasattr(response, 'words') and response.words:
        for w in response.words:
            words.append(Word(
                text=w.word,
                start=w.start,
                end=w.end,
                confidence=1.0,
            ))
    
    return TranscriptResult(
        text=response.text,
        words=words,
        language=response.language if hasattr(response, 'language') else "en",
        duration=response.duration if hasattr(response, 'duration') else 0.0,
    )


def _transcribe_local(
    audio_path: str,
    model: str = "base",
    language: Optional[str] = None,
) -> TranscriptResult:
    """Transcribe using local faster-whisper."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError("faster-whisper package required: pip install faster-whisper")
    
    whisper_model = WhisperModel(model, device="auto", compute_type="auto")
    
    segments, info = whisper_model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
    )
    
    words = []
    full_text = []
    
    for segment in segments:
        full_text.append(segment.text)
        if segment.words:
            for w in segment.words:
                words.append(Word(
                    text=w.word,
                    start=w.start,
                    end=w.end,
                    confidence=w.probability,
                ))
    
    return TranscriptResult(
        text=" ".join(full_text),
        words=words,
        language=info.language,
        duration=info.duration,
    )
