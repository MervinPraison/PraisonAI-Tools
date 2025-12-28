"""Video rendering using FFmpeg."""

import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import List

try:
    from .plan import Segment, EditPlan
except ImportError:
    from plan import Segment, EditPlan


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


def render_video(
    input_path: str,
    output_path: str,
    plan: EditPlan,
    copy_codec: bool = True,
    verbose: bool = False,
) -> str:
    """
    Render video based on edit plan.
    
    Args:
        input_path: Path to input video
        output_path: Path for output video
        plan: EditPlan with segments to keep
        copy_codec: If True, copy codecs (faster). If False, re-encode.
        verbose: Print FFmpeg output
        
    Returns:
        Path to rendered video
        
    Raises:
        FileNotFoundError: If input file or ffmpeg not found
        RuntimeError: If rendering fails
    """
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    ffmpeg = _find_ffmpeg()
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Get keep segments
    keep_segments = plan.get_keep_segments()
    
    if not keep_segments:
        raise ValueError("No segments to keep in edit plan")
    
    # If only one segment, use simple trim
    if len(keep_segments) == 1:
        seg = keep_segments[0]
        return _render_single_segment(
            ffmpeg, str(input_file), str(output_file),
            seg.start, seg.end, copy_codec, verbose
        )
    
    # Multiple segments - use concat demuxer
    return _render_concat(
        ffmpeg, str(input_file), str(output_file),
        keep_segments, copy_codec, verbose
    )


def _render_single_segment(
    ffmpeg: str,
    input_path: str,
    output_path: str,
    start: float,
    end: float,
    copy_codec: bool,
    verbose: bool,
) -> str:
    """Render a single segment."""
    duration = end - start
    
    cmd = [ffmpeg, "-y"]
    
    if copy_codec:
        # Seek before input for faster seeking with copy
        cmd.extend(["-ss", str(start)])
        cmd.extend(["-i", input_path])
        cmd.extend(["-t", str(duration)])
        cmd.extend(["-c", "copy"])
    else:
        cmd.extend(["-i", input_path])
        cmd.extend(["-ss", str(start)])
        cmd.extend(["-t", str(duration)])
        cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "23"])
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])
    
    cmd.append(output_path)
    
    _run_ffmpeg(cmd, verbose)
    return output_path


def _render_concat(
    ffmpeg: str,
    input_path: str,
    output_path: str,
    segments: List[Segment],
    copy_codec: bool,
    verbose: bool,
) -> str:
    """Render multiple segments using concat."""
    # Create temp directory for segment files
    with tempfile.TemporaryDirectory() as tmpdir:
        segment_files = []
        
        # Extract each segment
        for i, seg in enumerate(segments):
            seg_path = Path(tmpdir) / f"seg_{i:04d}.mp4"
            duration = seg.end - seg.start
            
            cmd = [
                ffmpeg, "-y",
                "-ss", str(seg.start),
                "-i", input_path,
                "-t", str(duration),
            ]
            
            if copy_codec:
                cmd.extend(["-c", "copy"])
            else:
                cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "23"])
                cmd.extend(["-c:a", "aac", "-b:a", "128k"])
            
            cmd.append(str(seg_path))
            _run_ffmpeg(cmd, verbose)
            segment_files.append(seg_path)
        
        # Create concat file
        concat_file = Path(tmpdir) / "concat.txt"
        with open(concat_file, "w") as f:
            for seg_path in segment_files:
                f.write(f"file '{seg_path}'\n")
        
        # Concat segments
        cmd = [
            ffmpeg, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            output_path
        ]
        _run_ffmpeg(cmd, verbose)
    
    return output_path


def _run_ffmpeg(cmd: List[str], verbose: bool) -> None:
    """Run FFmpeg command."""
    if verbose:
        result = subprocess.run(cmd)
    else:
        result = subprocess.run(cmd, capture_output=True)
    
    if result.returncode != 0:
        stderr = result.stderr.decode() if hasattr(result, 'stderr') and result.stderr else ""
        raise RuntimeError(f"FFmpeg failed: {stderr}")
