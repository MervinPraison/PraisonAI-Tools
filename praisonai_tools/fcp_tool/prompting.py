"""
LLM Prompting for Final Cut Pro Integration

Converts natural language instructions to EditIntent JSON using OpenAI SDK.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from pydantic import ValidationError

from .intent import (
    Asset,
    AudioRole,
    AudioSettings,
    EditIntent,
    Project,
    ProjectFormat,
    Segment,
    Timeline,
    get_format_preset,
)


EDIT_INTENT_SCHEMA = EditIntent.model_json_schema()

SYSTEM_PROMPT = """You are an expert video editor assistant that converts natural language editing instructions into structured JSON for Final Cut Pro.

You MUST output ONLY valid JSON that conforms to the EditIntent schema. No prose, no explanations, just JSON.

## CRITICAL RULES:
1. ONLY use media files from the provided media_paths list. NEVER invent file paths.
2. If the user requests media not in the list, add it to "missing_inputs" array.
3. For time-based edits without specific timestamps, set "needs_user_timestamps": true and use default concatenation order.
4. Use rational time format for all time values: "numerator/denominators" (e.g., "2500/2500s" = 1 second at 25fps)
5. Default timescale is fps * 100 (e.g., 25fps → 2500)

## CAPABILITIES (v1):
- Create projects with primary storyline
- Place asset clips in sequence
- Set audio roles (dialogue, music, effects)
- Add chapter markers
- Basic volume adjustments

## NOT IMPLEMENTED (store in operations but will warn):
- remove_pauses_over_seconds: Silence/pause removal
- loudness_target_lufs: Audio normalization
- zoom_punches: Ken Burns / zoom effects

## SCHEMA STRUCTURE:
{schema}

## EXAMPLE OUTPUT:
```json
{{
  "version": "1",
  "project": {{
    "name": "My Edit",
    "format": {{"width": 1920, "height": 1080, "fps": 25.0}},
    "audio": {{"layout": "stereo", "rate": 48000, "channels": 2}}
  }},
  "assets": [
    {{
      "id": "r2",
      "name": "interview",
      "path": "/path/to/interview.mov",
      "has_video": true,
      "has_audio": true
    }}
  ],
  "timeline": {{
    "segments": [
      {{
        "asset_id": "r2",
        "offset": "0/2500s",
        "start": "0/2500s",
        "duration": "5000/2500s",
        "lane": 0,
        "role": "dialogue"
      }}
    ],
    "markers": []
  }}
}}
```
"""

USER_PROMPT_TEMPLATE = """## INSTRUCTION:
{instruction}

## AVAILABLE MEDIA FILES:
{media_list}

## PROJECT SETTINGS:
- Project name: {project_name}
- Format: {format_info}

Generate the EditIntent JSON now. Output ONLY the JSON, no other text."""


def _get_openai_client():
    """Lazy import and create OpenAI client."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "OpenAI SDK not installed. Install with: pip install openai"
        )

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable not set. "
            "Set it with: export OPENAI_API_KEY=your-key"
        )

    return OpenAI(api_key=api_key)


def generate_edit_intent(
    instruction: str,
    media_paths: list[str],
    project_name: str = "Untitled Project",
    format_preset: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    fps: Optional[float] = None,
    model: str = "gpt-4o",
    max_retries: int = 3,
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> tuple[EditIntent, list[str]]:
    """
    Generate EditIntent from natural language instruction using OpenAI.
    
    Args:
        instruction: Natural language editing instruction
        media_paths: List of available media file paths
        project_name: Name for the project
        format_preset: Format preset name (e.g., "1080p25")
        width: Custom width (overrides preset)
        height: Custom height (overrides preset)
        fps: Custom fps (overrides preset)
        model: OpenAI model to use
        max_retries: Maximum retry attempts for validation
        agent_id: Agent ID for attribution
        run_id: Run ID for attribution
        session_id: Session ID for attribution
        
    Returns:
        Tuple of (EditIntent, warnings)
    """
    client = _get_openai_client()
    warnings = []

    for path in media_paths:
        if not os.path.isabs(path):
            raise ValueError(f"Media path must be absolute: {path}")
        if not os.path.exists(path):
            warnings.append(f"Media file not found (will be referenced anyway): {path}")

    if format_preset:
        project_format = get_format_preset(format_preset)
    else:
        project_format = ProjectFormat(
            width=width or 1920,
            height=height or 1080,
            fps=fps or 25.0,
        )

    if width:
        project_format.width = width
    if height:
        project_format.height = height
    if fps:
        project_format.fps = fps

    media_list = "\n".join(f"- {path}" for path in media_paths) or "No media files provided"
    format_info = f"{project_format.width}x{project_format.height} @ {project_format.fps}fps"

    system_prompt = SYSTEM_PROMPT.format(schema=json.dumps(EDIT_INTENT_SCHEMA, indent=2))
    user_prompt = USER_PROMPT_TEMPLATE.format(
        instruction=instruction,
        media_list=media_list,
        project_name=project_name,
        format_info=format_info,
    )

    last_error = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                user_prompt = f"{user_prompt}\n\n## PREVIOUS ERROR (attempt {attempt}):\n{last_error}\n\nPlease fix the JSON and try again."

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            content = response.choices[0].message.content
            if not content:
                last_error = "Empty response from LLM"
                continue

            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                last_error = f"Invalid JSON: {e}"
                continue

            data = _normalize_intent_data(data, media_paths, project_name, project_format)

            intent = EditIntent.model_validate(data)

            intent.agent_id = agent_id
            intent.run_id = run_id
            intent.session_id = session_id

            warnings.extend(intent.get_warnings())

            return intent, warnings

        except ValidationError as e:
            last_error = f"Schema validation error: {e}"
            continue
        except Exception as e:
            last_error = f"Error: {e}"
            continue

    raise ValueError(
        f"Failed to generate valid EditIntent after {max_retries} attempts. "
        f"Last error: {last_error}"
    )


def _normalize_intent_data(
    data: dict[str, Any],
    media_paths: list[str],
    project_name: str,
    project_format: ProjectFormat,
) -> dict[str, Any]:
    """
    Normalize and fill in missing fields in the intent data.
    
    Args:
        data: Raw data from LLM
        media_paths: Available media paths
        project_name: Project name
        project_format: Project format settings
        
    Returns:
        Normalized data dictionary
    """
    if "version" not in data:
        data["version"] = "1"

    if "project" not in data:
        data["project"] = {}

    if "name" not in data["project"]:
        data["project"]["name"] = project_name

    if "format" not in data["project"]:
        data["project"]["format"] = project_format.model_dump()
    else:
        fmt = data["project"]["format"]
        if "width" not in fmt:
            fmt["width"] = project_format.width
        if "height" not in fmt:
            fmt["height"] = project_format.height
        if "fps" not in fmt:
            fmt["fps"] = project_format.fps

    if "audio" not in data["project"]:
        data["project"]["audio"] = {"layout": "stereo", "rate": 48000, "channels": 2}

    if "assets" not in data or not data["assets"]:
        data["assets"] = []
        for i, path in enumerate(media_paths):
            ext = os.path.splitext(path)[1].lower()
            has_video = ext in (".mov", ".mp4", ".m4v", ".avi", ".mkv", ".webm")
            has_audio = ext in (".wav", ".mp3", ".aac", ".m4a", ".aiff") or has_video

            data["assets"].append({
                "id": f"r{i + 2}",
                "name": os.path.basename(path),
                "path": path,
                "has_video": has_video,
                "has_audio": has_audio,
            })

    for asset in data["assets"]:
        if "id" not in asset:
            asset["id"] = f"r{data['assets'].index(asset) + 2}"
        if "name" not in asset:
            asset["name"] = os.path.basename(asset.get("path", "unknown"))

    if "timeline" not in data:
        data["timeline"] = {"segments": [], "markers": []}

    if "segments" not in data["timeline"]:
        data["timeline"]["segments"] = []

    if "markers" not in data["timeline"]:
        data["timeline"]["markers"] = []

    if not data["timeline"]["segments"] and data["assets"]:
        fps = data["project"]["format"].get("fps", 25.0)
        timescale = int(fps * 100)
        offset = 0

        for asset in data["assets"]:
            duration_seconds = 10.0
            duration_frames = int(duration_seconds * timescale)

            data["timeline"]["segments"].append({
                "asset_id": asset["id"],
                "offset": f"{offset}/{timescale}s",
                "start": f"0/{timescale}s",
                "duration": f"{duration_frames}/{timescale}s",
                "lane": 0,
            })
            offset += duration_frames

    return data


def create_simple_intent(
    media_paths: list[str],
    project_name: str = "Simple Project",
    format_preset: str = "1080p25",
) -> EditIntent:
    """
    Create a simple EditIntent that concatenates all media files.
    
    This is useful for testing or when LLM is not available.
    
    Args:
        media_paths: List of media file paths
        project_name: Project name
        format_preset: Format preset name
        
    Returns:
        EditIntent with all media concatenated
    """
    project_format = get_format_preset(format_preset)
    timescale = project_format.get_timescale()

    assets = []
    segments = []
    offset = 0

    for i, path in enumerate(media_paths):
        if not os.path.isabs(path):
            raise ValueError(f"Media path must be absolute: {path}")

        ext = os.path.splitext(path)[1].lower()
        has_video = ext in (".mov", ".mp4", ".m4v", ".avi", ".mkv", ".webm")
        has_audio = ext in (".wav", ".mp3", ".aac", ".m4a", ".aiff") or has_video

        asset_id = f"r{i + 2}"
        assets.append(Asset(
            id=asset_id,
            name=os.path.basename(path),
            path=path,
            has_video=has_video,
            has_audio=has_audio,
            format_ref="r1" if has_video else None,
        ))

        duration_frames = 10 * timescale

        segments.append(Segment(
            asset_id=asset_id,
            offset=f"{offset}/{timescale}s",
            start=f"0/{timescale}s",
            duration=f"{duration_frames}/{timescale}s",
            lane=0,
            role=AudioRole.DIALOGUE if has_audio else None,
        ))
        offset += duration_frames

    return EditIntent(
        version="1",
        project=Project(
            name=project_name,
            format=project_format,
            audio=AudioSettings(),
        ),
        assets=assets,
        timeline=Timeline(segments=segments, markers=[]),
    )
