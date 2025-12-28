# Video Module

## Installation

```python
pip install praisonai-tools
```

## Code Usage

```python
from praisonai_tools.video import (
    probe_video,
    transcribe_video,
    create_edit_plan,
    render_video,
    edit_video,
)

# Probe video metadata
result = probe_video("input.mp4")
print(f"Duration: {result.duration}s")
print(f"Resolution: {result.width}x{result.height}")

# Transcribe audio
transcript = transcribe_video("input.mp4")
print(transcript.text)
print(transcript.to_srt())

# Create edit plan
plan = create_edit_plan(
    transcript=transcript,
    duration=result.duration,
    remove_fillers=True,
    remove_repetitions=True,
    remove_silence=True,
)

# Render video
render_video(
    input_path="input.mp4",
    output_path="output.mp4",
    plan=plan,
)

# Full pipeline
result = edit_video(
    input_path="input.mp4",
    output_path="edited.mp4",
    preset="podcast",
    remove_fillers=True,
    remove_repetitions=True,
    remove_silence=True,
    verbose=True,
)
```

## Classes

### VideoProbeResult

```python
@dataclass
class VideoProbeResult:
    path: str
    duration: float
    width: int
    height: int
    fps: float
    codec: str
    bitrate: int
    size_bytes: int
    audio_codec: Optional[str]
    audio_sample_rate: Optional[int]
    audio_channels: Optional[int]
```

### TranscriptResult

```python
@dataclass
class TranscriptResult:
    text: str
    words: List[Word]
    language: str
    duration: float
    
    def to_srt(self) -> str: ...
    def to_dict(self) -> dict: ...
```

### EditPlan

```python
@dataclass
class EditPlan:
    segments: List[Segment]
    original_duration: float
    edited_duration: float
    removed_duration: float
    removal_summary: Dict[str, float]
```

### VideoEditResult

```python
@dataclass
class VideoEditResult:
    input_path: str
    output_path: str
    probe: VideoProbeResult
    transcript: TranscriptResult
    plan: EditPlan
    success: bool
    error: Optional[str]
    artifacts: Dict[str, str]
```

## Presets

| Preset | Fillers | Repetitions | Silence | Tangents |
|--------|---------|-------------|---------|----------|
| podcast | ✓ | ✓ | ✓ | ✗ |
| meeting | ✓ | ✓ | ✓ | ✗ |
| course | ✓ | ✓ | ✓ | ✗ |
| clean | ✓ | ✓ | ✓ | ✓ |
