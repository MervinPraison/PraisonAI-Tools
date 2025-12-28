"""Video probing - extract metadata using FFprobe."""

import json
import subprocess
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass
class VideoProbeResult:
    """Result of video probe operation."""
    path: str
    duration: float
    width: int
    height: int
    fps: float
    codec: str
    audio_codec: Optional[str] = None
    audio_sample_rate: Optional[int] = None
    audio_channels: Optional[int] = None
    size_bytes: int = 0
    format_name: str = ""
    bit_rate: int = 0
    streams: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "codec": self.codec,
            "audio_codec": self.audio_codec,
            "audio_sample_rate": self.audio_sample_rate,
            "audio_channels": self.audio_channels,
            "size_bytes": self.size_bytes,
            "format_name": self.format_name,
            "bit_rate": self.bit_rate,
            "streams": self.streams,
        }


def _find_ffprobe() -> str:
    """Find ffprobe executable."""
    # Check PATH first
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        return ffprobe
    
    # Check common locations
    common_paths = [
        "/opt/homebrew/bin/ffprobe",
        "/usr/local/bin/ffprobe",
        "/usr/bin/ffprobe",
    ]
    for path in common_paths:
        if Path(path).exists():
            return path
    
    raise FileNotFoundError(
        "ffprobe not found. Install FFmpeg: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"
    )


def probe_video(video_path: str) -> VideoProbeResult:
    """
    Probe a video file to extract metadata.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        VideoProbeResult with video metadata
        
    Raises:
        FileNotFoundError: If video file or ffprobe not found
        RuntimeError: If ffprobe fails
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    ffprobe = _find_ffprobe()
    
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe failed: {e.stderr}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse ffprobe output: {e}")
    
    # Extract video stream info
    video_stream = None
    audio_stream = None
    
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and video_stream is None:
            video_stream = stream
        elif stream.get("codec_type") == "audio" and audio_stream is None:
            audio_stream = stream
    
    if video_stream is None:
        raise RuntimeError(f"No video stream found in: {video_path}")
    
    # Parse FPS from r_frame_rate (e.g., "30/1" or "30000/1001")
    fps_str = video_stream.get("r_frame_rate", "30/1")
    try:
        num, den = fps_str.split("/")
        fps = float(num) / float(den)
    except (ValueError, ZeroDivisionError):
        fps = 30.0
    
    format_info = data.get("format", {})
    
    return VideoProbeResult(
        path=str(path.absolute()),
        duration=float(format_info.get("duration", 0)),
        width=int(video_stream.get("width", 0)),
        height=int(video_stream.get("height", 0)),
        fps=fps,
        codec=video_stream.get("codec_name", "unknown"),
        audio_codec=audio_stream.get("codec_name") if audio_stream else None,
        audio_sample_rate=int(audio_stream.get("sample_rate", 0)) if audio_stream else None,
        audio_channels=int(audio_stream.get("channels", 0)) if audio_stream else None,
        size_bytes=int(format_info.get("size", 0)),
        format_name=format_info.get("format_name", ""),
        bit_rate=int(format_info.get("bit_rate", 0)),
        streams=data.get("streams", []),
    )
