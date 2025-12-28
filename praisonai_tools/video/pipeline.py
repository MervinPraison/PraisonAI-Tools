"""Main video editing pipeline."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from .probe import probe_video, VideoProbeResult
    from .transcribe import transcribe_video, TranscriptResult
    from .plan import create_edit_plan, EditPlan
    from .render import render_video
except ImportError:
    from probe import probe_video, VideoProbeResult
    from transcribe import transcribe_video, TranscriptResult
    from plan import create_edit_plan, EditPlan
    from render import render_video


@dataclass
class VideoEditResult:
    """Result of video editing operation."""
    input_path: str
    output_path: str
    probe: VideoProbeResult
    transcript: TranscriptResult
    plan: EditPlan
    success: bool = True
    error: Optional[str] = None
    artifacts: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_path": self.input_path,
            "output_path": self.output_path,
            "probe": self.probe.to_dict(),
            "transcript": self.transcript.to_dict(),
            "plan": self.plan.to_dict(),
            "success": self.success,
            "error": self.error,
            "artifacts": self.artifacts,
        }


def edit_video(
    input_path: str,
    output_path: Optional[str] = None,
    preset: str = "podcast",
    remove_fillers: bool = True,
    remove_repetitions: bool = True,
    remove_silence: bool = True,
    remove_tangents: bool = False,
    min_silence: float = 1.5,
    use_local_whisper: bool = False,
    copy_codec: bool = True,
    verbose: bool = False,
    save_artifacts: bool = True,
) -> VideoEditResult:
    """
    Full video editing pipeline.
    
    Args:
        input_path: Path to input video
        output_path: Path for output video (default: input_edited.mp4)
        preset: Edit preset (podcast, meeting, course, clean)
        remove_fillers: Remove filler words
        remove_repetitions: Remove repeated words
        remove_silence: Remove long silences
        remove_tangents: Use LLM to detect off-topic content
        min_silence: Minimum silence duration to remove
        use_local_whisper: Use local faster-whisper instead of OpenAI
        copy_codec: Copy codecs (faster) vs re-encode
        verbose: Print detailed progress
        save_artifacts: Save transcript, plan, etc. as files
        
    Returns:
        VideoEditResult with all outputs and artifacts
    """
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Determine output path
    if output_path is None:
        output_path = str(input_file.parent / f"{input_file.stem}_edited{input_file.suffix}")
    
    output_file = Path(output_path)
    artifacts_dir = output_file.parent / f".praison/video/{input_file.stem}"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    artifacts = {}
    
    # Apply preset settings
    preset_config = _get_preset_config(preset)
    if preset_config:
        remove_fillers = preset_config.get("remove_fillers", remove_fillers)
        remove_repetitions = preset_config.get("remove_repetitions", remove_repetitions)
        remove_silence = preset_config.get("remove_silence", remove_silence)
        remove_tangents = preset_config.get("remove_tangents", remove_tangents)
        min_silence = preset_config.get("min_silence", min_silence)
    
    try:
        # Step 1: Probe video
        if verbose:
            print(f"[1/4] Probing video: {input_path}")
        probe = probe_video(input_path)
        
        if save_artifacts:
            probe_path = artifacts_dir / "probe.json"
            with open(probe_path, "w") as f:
                json.dump(probe.to_dict(), f, indent=2)
            artifacts["probe"] = str(probe_path)
        
        # Step 2: Transcribe
        if verbose:
            print(f"[2/4] Transcribing audio ({probe.duration:.1f}s)...")
        transcript = transcribe_video(
            input_path,
            use_local=use_local_whisper,
        )
        
        if save_artifacts:
            # Save transcript text
            txt_path = artifacts_dir / "transcript.txt"
            with open(txt_path, "w") as f:
                f.write(transcript.text)
            artifacts["transcript_txt"] = str(txt_path)
            
            # Save SRT
            srt_path = artifacts_dir / "transcript.srt"
            with open(srt_path, "w") as f:
                f.write(transcript.to_srt())
            artifacts["transcript_srt"] = str(srt_path)
            
            # Save full transcript JSON
            json_path = artifacts_dir / "transcript.json"
            with open(json_path, "w") as f:
                json.dump(transcript.to_dict(), f, indent=2)
            artifacts["transcript_json"] = str(json_path)
        
        # Step 3: Create edit plan
        if verbose:
            print("[3/4] Analyzing content and creating edit plan...")
        plan = create_edit_plan(
            transcript=transcript,
            duration=probe.duration,
            remove_fillers=remove_fillers,
            remove_repetitions=remove_repetitions,
            remove_silence=remove_silence,
            remove_tangents=remove_tangents,
            min_silence=min_silence,
            use_llm=remove_tangents,
        )
        
        if save_artifacts:
            plan_path = artifacts_dir / "plan.json"
            with open(plan_path, "w") as f:
                json.dump(plan.to_dict(), f, indent=2)
            artifacts["plan"] = str(plan_path)
        
        if verbose:
            print(f"    Original: {plan.original_duration:.1f}s")
            print(f"    Edited:   {plan.edited_duration:.1f}s")
            print(f"    Removed:  {plan.removed_duration:.1f}s ({plan.removed_duration/plan.original_duration*100:.1f}%)")
            for cat, dur in plan.removal_summary.items():
                print(f"      - {cat}: {dur:.1f}s")
        
        # Step 4: Render
        if verbose:
            print(f"[4/4] Rendering output: {output_path}")
        
        render_video(
            input_path=input_path,
            output_path=output_path,
            plan=plan,
            copy_codec=copy_codec,
            verbose=verbose,
        )
        artifacts["output"] = output_path
        
        if verbose:
            print(f"\n✓ Done! Output: {output_path}")
        
        return VideoEditResult(
            input_path=input_path,
            output_path=output_path,
            probe=probe,
            transcript=transcript,
            plan=plan,
            success=True,
            artifacts=artifacts,
        )
        
    except Exception as e:
        return VideoEditResult(
            input_path=input_path,
            output_path=output_path,
            probe=probe if 'probe' in dir() else None,
            transcript=transcript if 'transcript' in dir() else None,
            plan=plan if 'plan' in dir() else None,
            success=False,
            error=str(e),
            artifacts=artifacts,
        )


def _get_preset_config(preset: str) -> Dict[str, Any]:
    """Get configuration for a preset."""
    presets = {
        "podcast": {
            "remove_fillers": True,
            "remove_repetitions": True,
            "remove_silence": True,
            "remove_tangents": False,
            "min_silence": 1.5,
        },
        "meeting": {
            "remove_fillers": True,
            "remove_repetitions": False,
            "remove_silence": True,
            "remove_tangents": False,
            "min_silence": 2.0,
        },
        "course": {
            "remove_fillers": True,
            "remove_repetitions": True,
            "remove_silence": True,
            "remove_tangents": True,
            "min_silence": 1.0,
        },
        "clean": {
            "remove_fillers": True,
            "remove_repetitions": True,
            "remove_silence": True,
            "remove_tangents": True,
            "min_silence": 0.8,
        },
    }
    return presets.get(preset, {})
