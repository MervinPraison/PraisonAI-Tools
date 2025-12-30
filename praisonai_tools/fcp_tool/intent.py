"""
EditIntent Pydantic Schema for Final Cut Pro Integration

This module defines the structured data models for representing video editing
intents that can be converted to FCPXML for Final Cut Pro.
"""

from __future__ import annotations

import hashlib
import os
import re
from enum import Enum
from typing import Any, Optional
from urllib.parse import quote

from pydantic import BaseModel, Field, field_validator, model_validator


class AudioRole(str, Enum):
    """Audio roles supported in FCPXML."""
    DIALOGUE = "dialogue"
    MUSIC = "music"
    EFFECTS = "effects"


class AudioLayout(str, Enum):
    """Audio channel layouts."""
    MONO = "mono"
    STEREO = "stereo"
    SURROUND = "surround"


class ProjectFormat(BaseModel):
    """Video format specification for the project."""
    width: int = Field(default=1920, ge=1, description="Frame width in pixels")
    height: int = Field(default=1080, ge=1, description="Frame height in pixels")
    fps: float = Field(default=25.0, gt=0, description="Frames per second")
    frame_duration_rational: Optional[str] = Field(
        default=None,
        description="Rational frame duration (e.g., '100/2500s'). Auto-calculated if not provided."
    )

    @model_validator(mode="after")
    def calculate_frame_duration(self) -> "ProjectFormat":
        """Auto-calculate rational frame duration from fps if not provided."""
        if self.frame_duration_rational is None:
            timescale = int(self.fps * 100)
            self.frame_duration_rational = f"100/{timescale}s"
        return self

    def get_timescale(self) -> int:
        """Get the timescale for rational time calculations."""
        return int(self.fps * 100)


class AudioSettings(BaseModel):
    """Audio settings for the project."""
    layout: AudioLayout = Field(default=AudioLayout.STEREO)
    rate: int = Field(default=48000, description="Audio sample rate in Hz")
    channels: int = Field(default=2, ge=1, description="Number of audio channels")


class Asset(BaseModel):
    """Represents a media asset (video/audio file)."""
    id: str = Field(description="Internal reference ID (e.g., 'r2', 'r3')")
    name: str = Field(description="Display name for the asset")
    path: str = Field(description="Absolute local file path")
    uid: Optional[str] = Field(default=None, description="Stable hash UID for the asset")
    has_video: bool = Field(default=True, description="Whether asset contains video")
    has_audio: bool = Field(default=True, description="Whether asset contains audio")
    format_ref: Optional[str] = Field(
        default=None,
        description="Reference to format definition (e.g., 'r1')"
    )
    audio_rate: int = Field(default=48000, description="Audio sample rate")
    audio_channels: int = Field(default=2, description="Number of audio channels")
    duration_rational: Optional[str] = Field(
        default=None,
        description="Asset duration as rational time (e.g., '12000/2500s')"
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate that path is absolute."""
        if not os.path.isabs(v):
            raise ValueError(f"Asset path must be absolute: {v}")
        return v

    @model_validator(mode="after")
    def generate_uid(self) -> "Asset":
        """Generate stable UID from path if not provided."""
        if self.uid is None:
            self.uid = hashlib.sha256(self.path.encode()).hexdigest()[:32].upper()
        return self

    def get_src_url(self) -> str:
        """Get file:// URL for the asset path."""
        return f"file://{quote(self.path, safe='/:')}"


class Segment(BaseModel):
    """Represents a timeline segment (clip placement)."""
    asset_id: str = Field(description="Reference to asset ID")
    offset: str = Field(
        description="Timeline position as rational time (e.g., '0/2500s')"
    )
    start: str = Field(
        default="0/2500s",
        description="Source start point as rational time"
    )
    duration: str = Field(
        description="Segment duration as rational time (e.g., '5000/2500s')"
    )
    lane: int = Field(default=0, description="Timeline lane (0 = primary storyline)")
    role: Optional[AudioRole] = Field(default=None, description="Audio role assignment")
    volume: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Volume adjustment (1.0 = unity gain)"
    )
    name: Optional[str] = Field(default=None, description="Optional clip name override")

    @field_validator("offset", "start", "duration")
    @classmethod
    def validate_rational_time(cls, v: str) -> str:
        """Validate rational time format."""
        if not re.match(r"^\d+/\d+s$", v):
            raise ValueError(f"Invalid rational time format: {v}. Expected format: '1234/2500s'")
        return v


class Marker(BaseModel):
    """Represents a timeline marker (chapter point)."""
    name: str = Field(description="Marker name/label")
    start: str = Field(description="Marker position as rational time")
    duration: str = Field(default="0/2500s", description="Marker duration")

    @field_validator("start", "duration")
    @classmethod
    def validate_rational_time(cls, v: str) -> str:
        """Validate rational time format."""
        if not re.match(r"^\d+/\d+s$", v):
            raise ValueError(f"Invalid rational time format: {v}. Expected format: '1234/2500s'")
        return v


class Operations(BaseModel):
    """Optional processing operations (may not all be implemented)."""
    remove_pauses_over_seconds: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Remove pauses longer than this duration (NOT IMPLEMENTED)"
    )
    loudness_target_lufs: Optional[float] = Field(
        default=None,
        le=0.0,
        description="Target loudness in LUFS (NOT IMPLEMENTED)"
    )
    zoom_punches: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Zoom punch-in effects (NOT IMPLEMENTED)"
    )

    def get_unimplemented_warnings(self) -> list[str]:
        """Return warnings for operations that are requested but not implemented."""
        warnings = []
        if self.remove_pauses_over_seconds is not None:
            warnings.append(
                f"Operation 'remove_pauses_over_seconds={self.remove_pauses_over_seconds}' "
                "is NOT IMPLEMENTED - pauses will not be removed"
            )
        if self.loudness_target_lufs is not None:
            warnings.append(
                f"Operation 'loudness_target_lufs={self.loudness_target_lufs}' "
                "is NOT IMPLEMENTED - loudness will not be adjusted"
            )
        if self.zoom_punches:
            warnings.append(
                f"Operation 'zoom_punches' with {len(self.zoom_punches)} entries "
                "is NOT IMPLEMENTED - zoom effects will not be applied"
            )
        return warnings


class Timeline(BaseModel):
    """Timeline structure containing segments and markers."""
    segments: list[Segment] = Field(default_factory=list)
    markers: list[Marker] = Field(default_factory=list)


class Project(BaseModel):
    """Project metadata."""
    name: str = Field(description="Project name")
    format: ProjectFormat = Field(default_factory=ProjectFormat)
    audio: AudioSettings = Field(default_factory=AudioSettings)


class EditIntent(BaseModel):
    """
    Complete edit intent specification.
    
    This is the top-level schema that represents a complete video editing
    instruction that can be converted to FCPXML.
    """
    version: str = Field(default="1", description="Schema version")
    project: Project = Field(description="Project metadata")
    assets: list[Asset] = Field(default_factory=list, description="Media assets")
    timeline: Timeline = Field(default_factory=Timeline, description="Timeline structure")
    operations: Optional[Operations] = Field(
        default=None,
        description="Optional processing operations"
    )
    agent_id: Optional[str] = Field(default=None, description="Agent ID for attribution")
    run_id: Optional[str] = Field(default=None, description="Run ID for attribution")
    session_id: Optional[str] = Field(default=None, description="Session ID for attribution")
    missing_inputs: Optional[list[str]] = Field(
        default=None,
        description="List of missing inputs that were requested but not provided"
    )
    needs_user_timestamps: bool = Field(
        default=False,
        description="True if user needs to provide specific timestamps"
    )

    @model_validator(mode="after")
    def validate_asset_references(self) -> "EditIntent":
        """Validate that all segment asset_ids reference valid assets."""
        asset_ids = {asset.id for asset in self.assets}
        for segment in self.timeline.segments:
            if segment.asset_id not in asset_ids:
                raise ValueError(
                    f"Segment references unknown asset_id '{segment.asset_id}'. "
                    f"Valid asset IDs: {asset_ids}"
                )
        return self

    def get_warnings(self) -> list[str]:
        """Get all warnings for this intent."""
        warnings = []
        if self.operations:
            warnings.extend(self.operations.get_unimplemented_warnings())
        if self.missing_inputs:
            warnings.append(
                f"Missing inputs requested: {', '.join(self.missing_inputs)}"
            )
        if self.needs_user_timestamps:
            warnings.append(
                "User timestamps needed - using default concatenation order"
            )
        return warnings

    def get_asset_by_id(self, asset_id: str) -> Optional[Asset]:
        """Get an asset by its ID."""
        for asset in self.assets:
            if asset.id == asset_id:
                return asset
        return None

    @classmethod
    def get_json_schema(cls) -> dict:
        """Get the JSON schema for this model."""
        return cls.model_json_schema()


def seconds_to_rational(seconds: float, fps: float = 25.0) -> str:
    """
    Convert seconds to rational time string.
    
    Args:
        seconds: Time in seconds
        fps: Frames per second for timescale calculation
        
    Returns:
        Rational time string (e.g., '2500/2500s' for 1 second at 25fps)
    """
    timescale = int(fps * 100)
    frames = int(round(seconds * timescale))
    return f"{frames}/{timescale}s"


def rational_to_seconds(rational: str) -> float:
    """
    Convert rational time string to seconds.
    
    Args:
        rational: Rational time string (e.g., '2500/2500s')
        
    Returns:
        Time in seconds
    """
    match = re.match(r"^(\d+)/(\d+)s$", rational)
    if not match:
        raise ValueError(f"Invalid rational time format: {rational}")
    numerator = int(match.group(1))
    denominator = int(match.group(2))
    return numerator / denominator


FORMAT_PRESETS = {
    "1080p25": ProjectFormat(width=1920, height=1080, fps=25.0),
    "1080p30": ProjectFormat(width=1920, height=1080, fps=30.0),
    "1080p24": ProjectFormat(width=1920, height=1080, fps=24.0),
    "1080p50": ProjectFormat(width=1920, height=1080, fps=50.0),
    "1080p60": ProjectFormat(width=1920, height=1080, fps=60.0),
    "4k25": ProjectFormat(width=3840, height=2160, fps=25.0),
    "4k30": ProjectFormat(width=3840, height=2160, fps=30.0),
    "4k24": ProjectFormat(width=3840, height=2160, fps=24.0),
    "4k50": ProjectFormat(width=3840, height=2160, fps=50.0),
    "4k60": ProjectFormat(width=3840, height=2160, fps=60.0),
    "720p25": ProjectFormat(width=1280, height=720, fps=25.0),
    "720p30": ProjectFormat(width=1280, height=720, fps=30.0),
}


def get_format_preset(name: str) -> ProjectFormat:
    """Get a format preset by name."""
    if name not in FORMAT_PRESETS:
        raise ValueError(
            f"Unknown format preset: {name}. "
            f"Available presets: {', '.join(FORMAT_PRESETS.keys())}"
        )
    return FORMAT_PRESETS[name].model_copy()


# Rebuild models to resolve forward references
ProjectFormat.model_rebuild()
AudioSettings.model_rebuild()
Asset.model_rebuild()
Segment.model_rebuild()
Marker.model_rebuild()
Operations.model_rebuild()
Timeline.model_rebuild()
Project.model_rebuild()
EditIntent.model_rebuild()
