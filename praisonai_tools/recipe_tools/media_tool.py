"""
Media Tool - Audio/video operations via ffmpeg.

Provides:
- Probing media files for metadata
- Extracting audio from video
- Normalizing audio levels
- Trimming media files
- Extracting frames from video
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

import sys
import os
_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

try:
    from .base import RecipeToolBase
except ImportError:
    from base import RecipeToolBase

logger = logging.getLogger(__name__)


@dataclass
class MediaProbeResult:
    """Result of probing a media file."""
    path: str
    duration: float  # seconds
    format_name: str
    format_long_name: str
    size: int  # bytes
    bit_rate: int  # bits per second
    # Video stream info (if present)
    has_video: bool = False
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    video_codec: Optional[str] = None
    # Audio stream info (if present)
    has_audio: bool = False
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    audio_codec: Optional[str] = None
    # Raw data
    streams: List[Dict] = field(default_factory=list)
    format_info: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "duration": self.duration,
            "format_name": self.format_name,
            "format_long_name": self.format_long_name,
            "size": self.size,
            "bit_rate": self.bit_rate,
            "has_video": self.has_video,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "video_codec": self.video_codec,
            "has_audio": self.has_audio,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "audio_codec": self.audio_codec,
        }


class MediaTool(RecipeToolBase):
    """
    Media operations tool using ffmpeg/ffprobe.
    
    Provides audio/video probing, extraction, normalization, trimming, and frame extraction.
    """
    
    name = "media_tool"
    description = "Audio/video operations via ffmpeg"
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check for ffmpeg and ffprobe."""
        return {
            "ffmpeg": self._check_binary("ffmpeg"),
            "ffprobe": self._check_binary("ffprobe"),
        }
    
    def probe(self, path: Union[str, Path]) -> MediaProbeResult:
        """
        Probe a media file for metadata.
        
        Args:
            path: Path to media file
            
        Returns:
            MediaProbeResult with file metadata
        """
        self.require_dependencies(["ffprobe"])
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Media file not found: {path}")
        
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path)
        ]
        
        result = self._run_command(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")
        
        data = json.loads(result.stdout)
        format_info = data.get("format", {})
        streams = data.get("streams", [])
        
        # Parse format info
        duration = float(format_info.get("duration", 0))
        size = int(format_info.get("size", 0))
        bit_rate = int(format_info.get("bit_rate", 0))
        
        # Find video and audio streams
        video_stream = None
        audio_stream = None
        for stream in streams:
            if stream.get("codec_type") == "video" and not video_stream:
                video_stream = stream
            elif stream.get("codec_type") == "audio" and not audio_stream:
                audio_stream = stream
        
        # Parse video info
        has_video = video_stream is not None
        width = None
        height = None
        fps = None
        video_codec = None
        if video_stream:
            width = video_stream.get("width")
            height = video_stream.get("height")
            video_codec = video_stream.get("codec_name")
            # Parse frame rate
            fps_str = video_stream.get("r_frame_rate", "0/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = float(num) / float(den) if float(den) > 0 else 0
            else:
                fps = float(fps_str)
        
        # Parse audio info
        has_audio = audio_stream is not None
        sample_rate = None
        channels = None
        audio_codec = None
        if audio_stream:
            sample_rate = int(audio_stream.get("sample_rate", 0))
            channels = audio_stream.get("channels")
            audio_codec = audio_stream.get("codec_name")
        
        return MediaProbeResult(
            path=str(path),
            duration=duration,
            format_name=format_info.get("format_name", ""),
            format_long_name=format_info.get("format_long_name", ""),
            size=size,
            bit_rate=bit_rate,
            has_video=has_video,
            width=width,
            height=height,
            fps=fps,
            video_codec=video_codec,
            has_audio=has_audio,
            sample_rate=sample_rate,
            channels=channels,
            audio_codec=audio_codec,
            streams=streams,
            format_info=format_info,
        )
    
    def extract_audio(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        format: str = "mp3",
        bitrate: str = "192k",
    ) -> Path:
        """
        Extract audio track from video file.
        
        Args:
            input_path: Input video file
            output_path: Output audio file (auto-generated if not provided)
            format: Output format (mp3, wav, m4a, flac)
            bitrate: Audio bitrate
            
        Returns:
            Path to extracted audio file
        """
        self.require_dependencies(["ffmpeg"])
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        if output_path is None:
            output_path = self._generate_output_path(input_path, extension=format)
        else:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
        
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-i", str(input_path),
            "-vn",  # No video
            "-acodec", self._get_audio_codec(format),
            "-b:a", bitrate,
            str(output_path)
        ]
        
        result = self._run_command(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"Audio extraction failed: {result.stderr}")
        
        return output_path
    
    def normalize(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        target_lufs: float = -16.0,
        target_tp: float = -1.5,
    ) -> Path:
        """
        Normalize audio loudness using EBU R128 standard.
        
        Args:
            input_path: Input audio/video file
            output_path: Output file (auto-generated if not provided)
            target_lufs: Target integrated loudness (default: -16 LUFS)
            target_tp: Target true peak (default: -1.5 dB)
            
        Returns:
            Path to normalized file
        """
        self.require_dependencies(["ffmpeg"])
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        if output_path is None:
            output_path = self._generate_output_path(input_path, suffix="_normalized")
        else:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
        
        # Two-pass loudnorm filter
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-af", f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=11",
            "-ar", "48000",
            str(output_path)
        ]
        
        result = self._run_command(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"Normalization failed: {result.stderr}")
        
        return output_path
    
    def trim(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        start: Optional[float] = None,
        end: Optional[float] = None,
        duration: Optional[float] = None,
    ) -> Path:
        """
        Trim media file to specified time range.
        
        Args:
            input_path: Input file
            output_path: Output file (auto-generated if not provided)
            start: Start time in seconds
            end: End time in seconds
            duration: Duration in seconds (alternative to end)
            
        Returns:
            Path to trimmed file
        """
        self.require_dependencies(["ffmpeg"])
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        if output_path is None:
            output_path = self._generate_output_path(input_path, suffix="_trimmed")
        else:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
        
        cmd = ["ffmpeg", "-y", "-i", str(input_path)]
        
        if start is not None:
            cmd.extend(["-ss", str(start)])
        
        if end is not None:
            cmd.extend(["-to", str(end)])
        elif duration is not None:
            cmd.extend(["-t", str(duration)])
        
        cmd.extend(["-c", "copy", str(output_path)])
        
        result = self._run_command(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"Trim failed: {result.stderr}")
        
        return output_path
    
    def extract_frames(
        self,
        input_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        interval: float = 10.0,
        count: Optional[int] = None,
        format: str = "jpg",
        quality: int = 2,
    ) -> List[Path]:
        """
        Extract frames from video at specified intervals.
        
        Args:
            input_path: Input video file
            output_dir: Output directory for frames
            interval: Interval between frames in seconds
            count: Exact number of frames to extract (overrides interval)
            format: Output image format (jpg, png)
            quality: JPEG quality (1-31, lower is better)
            
        Returns:
            List of paths to extracted frames
        """
        self.require_dependencies(["ffmpeg"])
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        if output_dir is None:
            output_dir = input_path.parent / f"{input_path.stem}_frames"
        else:
            output_dir = Path(output_dir)
        
        self._ensure_output_dir(output_dir)
        
        # Get video duration for count-based extraction
        if count is not None:
            probe = self.probe(input_path)
            interval = probe.duration / count if count > 0 else 10.0
        
        output_pattern = str(output_dir / f"frame_%04d.{format}")
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-vf", f"fps=1/{interval}",
            "-q:v", str(quality),
            output_pattern
        ]
        
        result = self._run_command(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"Frame extraction failed: {result.stderr}")
        
        # Collect extracted frames
        frames = sorted(output_dir.glob(f"frame_*.{format}"))
        return frames
    
    def remove_silence(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        noise_threshold: str = "-50dB",
        min_silence_duration: float = 0.5,
    ) -> Path:
        """
        Remove silence from audio/video file.
        
        Args:
            input_path: Input file
            output_path: Output file (auto-generated if not provided)
            noise_threshold: Silence detection threshold
            min_silence_duration: Minimum silence duration to remove (seconds)
            
        Returns:
            Path to processed file
        """
        self.require_dependencies(["ffmpeg"])
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        if output_path is None:
            output_path = self._generate_output_path(input_path, suffix="_nosilence")
        else:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
        
        # Use silenceremove filter
        filter_str = (
            f"silenceremove=start_periods=1:start_duration=0:"
            f"start_threshold={noise_threshold}:"
            f"stop_periods=-1:stop_duration={min_silence_duration}:"
            f"stop_threshold={noise_threshold}"
        )
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-af", filter_str,
            str(output_path)
        ]
        
        result = self._run_command(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"Silence removal failed: {result.stderr}")
        
        return output_path
    
    def create_gif(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        start: float = 0,
        duration: float = 5,
        fps: int = 10,
        width: int = 480,
    ) -> Path:
        """
        Create GIF from video.
        
        Args:
            input_path: Input video file
            output_path: Output GIF file
            start: Start time in seconds
            duration: Duration in seconds
            fps: Frames per second
            width: Output width (height auto-scaled)
            
        Returns:
            Path to created GIF
        """
        self.require_dependencies(["ffmpeg"])
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        if output_path is None:
            output_path = self._generate_output_path(input_path, extension="gif")
        else:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
        
        # Generate palette for better quality
        palette_path = output_path.parent / f".palette_{output_path.stem}.png"
        
        filter_str = f"fps={fps},scale={width}:-1:flags=lanczos"
        
        # Pass 1: Generate palette
        cmd1 = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-t", str(duration),
            "-i", str(input_path),
            "-vf", f"{filter_str},palettegen",
            str(palette_path)
        ]
        
        result = self._run_command(cmd1)
        if result.returncode != 0:
            raise RuntimeError(f"Palette generation failed: {result.stderr}")
        
        # Pass 2: Create GIF with palette
        cmd2 = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-t", str(duration),
            "-i", str(input_path),
            "-i", str(palette_path),
            "-lavfi", f"{filter_str} [x]; [x][1:v] paletteuse",
            str(output_path)
        ]
        
        result = self._run_command(cmd2)
        
        # Clean up palette
        if palette_path.exists():
            palette_path.unlink()
        
        if result.returncode != 0:
            raise RuntimeError(f"GIF creation failed: {result.stderr}")
        
        return output_path
    
    def _get_audio_codec(self, format: str) -> str:
        """Get ffmpeg audio codec for format."""
        codecs = {
            "mp3": "libmp3lame",
            "m4a": "aac",
            "aac": "aac",
            "wav": "pcm_s16le",
            "flac": "flac",
            "ogg": "libvorbis",
        }
        return codecs.get(format.lower(), "libmp3lame")


# Convenience functions
def media_probe(path: Union[str, Path], verbose: bool = False) -> MediaProbeResult:
    """Probe a media file for metadata."""
    return MediaTool(verbose=verbose).probe(path)


def media_extract_audio(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    format: str = "mp3",
    bitrate: str = "192k",
    verbose: bool = False,
) -> Path:
    """Extract audio from video file."""
    return MediaTool(verbose=verbose).extract_audio(input_path, output_path, format, bitrate)


def media_normalize(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    target_lufs: float = -16.0,
    verbose: bool = False,
) -> Path:
    """Normalize audio loudness."""
    return MediaTool(verbose=verbose).normalize(input_path, output_path, target_lufs)


def media_trim(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    start: Optional[float] = None,
    end: Optional[float] = None,
    duration: Optional[float] = None,
    verbose: bool = False,
) -> Path:
    """Trim media file."""
    return MediaTool(verbose=verbose).trim(input_path, output_path, start, end, duration)


def media_extract_frames(
    input_path: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    interval: float = 10.0,
    count: Optional[int] = None,
    verbose: bool = False,
) -> List[Path]:
    """Extract frames from video."""
    return MediaTool(verbose=verbose).extract_frames(input_path, output_dir, interval, count)
