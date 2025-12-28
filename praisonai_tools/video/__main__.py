"""CLI entry point for praisonai_tools.video.

Usage:
    python -m praisonai_tools.video edit input.mp4 --output edited.mp4
    python -m praisonai_tools.video probe input.mp4
    python -m praisonai_tools.video transcribe input.mp4 --output transcript.srt
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for standalone execution
if __name__ == "__main__":
    _parent = Path(__file__).parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))


def main():
    parser = argparse.ArgumentParser(
        prog="praisonai-video",
        description="AI-powered video editing tools",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Probe command
    probe_parser = subparsers.add_parser("probe", help="Probe video metadata")
    probe_parser.add_argument("input", help="Input video file")
    probe_parser.add_argument("--output", "-o", help="Output JSON file")
    probe_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Transcribe command
    trans_parser = subparsers.add_parser("transcribe", help="Transcribe video audio")
    trans_parser.add_argument("input", help="Input video file")
    trans_parser.add_argument("--output", "-o", help="Output file (txt, srt, or json)")
    trans_parser.add_argument("--format", choices=["txt", "srt", "json"], default="srt")
    trans_parser.add_argument("--local", action="store_true", help="Use local whisper")
    trans_parser.add_argument("--language", help="Language code (e.g., en)")
    
    # Plan command
    plan_parser = subparsers.add_parser("plan", help="Create edit plan from transcript")
    plan_parser.add_argument("input", help="Input video file")
    plan_parser.add_argument("--output", "-o", help="Output JSON file")
    plan_parser.add_argument("--preset", "-p", default="podcast",
                            choices=["podcast", "meeting", "course", "clean"])
    plan_parser.add_argument("--no-fillers", action="store_true")
    plan_parser.add_argument("--no-repetitions", action="store_true")
    plan_parser.add_argument("--no-silence", action="store_true")
    plan_parser.add_argument("--tangents", action="store_true")
    plan_parser.add_argument("--local", action="store_true", help="Use local whisper")
    
    # Render command
    render_parser = subparsers.add_parser("render", help="Render video from timeline")
    render_parser.add_argument("input", help="Input video file")
    render_parser.add_argument("--timeline", "-t", required=True, help="Timeline JSON file")
    render_parser.add_argument("--output", "-o", required=True, help="Output video file")
    render_parser.add_argument("--reencode", action="store_true", help="Re-encode video")
    
    # Edit command (full pipeline)
    edit_parser = subparsers.add_parser("edit", help="Full video editing pipeline")
    edit_parser.add_argument("input", help="Input video file")
    edit_parser.add_argument("--output", "-o", help="Output video file")
    edit_parser.add_argument("--workdir", "-w", help="Working directory for artifacts")
    edit_parser.add_argument("--preset", "-p", default="podcast",
                            choices=["podcast", "meeting", "course", "clean"])
    edit_parser.add_argument("--no-fillers", action="store_true", help="Keep filler words")
    edit_parser.add_argument("--no-repetitions", action="store_true", help="Keep repetitions")
    edit_parser.add_argument("--no-silence", action="store_true", help="Keep silences")
    edit_parser.add_argument("--tangents", action="store_true", help="Remove tangents")
    edit_parser.add_argument("--target-length", help="Target duration (e.g., 6m, 90s)")
    edit_parser.add_argument("--captions", choices=["off", "srt", "burn"], default="srt")
    edit_parser.add_argument("--force", action="store_true", help="Overwrite existing output")
    edit_parser.add_argument("--provider", choices=["openai", "local", "auto"], default="auto")
    edit_parser.add_argument("--no-llm", action="store_true", help="Use heuristics only")
    edit_parser.add_argument("--model", help="LLM model name")
    edit_parser.add_argument("--whisper-model", help="Whisper model name")
    edit_parser.add_argument("--local", action="store_true", help="Use local whisper")
    edit_parser.add_argument("--reencode", action="store_true", help="Re-encode video")
    edit_parser.add_argument("--verbose", "-v", action="store_true")
    edit_parser.add_argument("--no-artifacts", action="store_true", help="Don't save artifacts")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == "probe":
            return cmd_probe(args)
        elif args.command == "transcribe":
            return cmd_transcribe(args)
        elif args.command == "plan":
            return cmd_plan(args)
        elif args.command == "render":
            return cmd_render(args)
        elif args.command == "edit":
            return cmd_edit(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


def cmd_probe(args):
    """Handle probe command."""
    try:
        from .probe import probe_video
    except ImportError:
        from probe import probe_video
    
    result = probe_video(args.input)
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"Saved to: {args.output}")
    elif args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"File: {result.path}")
        print(f"Duration: {result.duration:.2f}s")
        print(f"Resolution: {result.width}x{result.height}")
        print(f"FPS: {result.fps:.2f}")
        print(f"Video codec: {result.codec}")
        if result.audio_codec:
            print(f"Audio codec: {result.audio_codec}")
            print(f"Audio: {result.audio_sample_rate}Hz, {result.audio_channels}ch")
        print(f"Size: {result.size_bytes / 1024 / 1024:.2f} MB")
    
    return 0


def cmd_transcribe(args):
    """Handle transcribe command."""
    try:
        from .transcribe import transcribe_video
    except ImportError:
        from transcribe import transcribe_video
    
    result = transcribe_video(
        args.input,
        use_local=args.local,
        language=args.language,
    )
    
    output_format = args.format
    if args.output:
        ext = Path(args.output).suffix.lower()
        if ext in [".txt", ".srt", ".json"]:
            output_format = ext[1:]
    
    if output_format == "txt":
        content = result.text
    elif output_format == "srt":
        content = result.to_srt()
    else:
        content = json.dumps(result.to_dict(), indent=2)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(content)
        print(f"Saved to: {args.output}")
    else:
        print(content)
    
    return 0


def cmd_plan(args):
    """Handle plan command."""
    try:
        from .probe import probe_video
        from .transcribe import transcribe_video
        from .plan import create_edit_plan
    except ImportError:
        from probe import probe_video
        from transcribe import transcribe_video
        from plan import create_edit_plan
    
    print(f"Probing: {args.input}")
    probe = probe_video(args.input)
    
    print(f"Transcribing ({probe.duration:.1f}s)...")
    transcript = transcribe_video(args.input, use_local=args.local)
    
    print("Creating edit plan...")
    plan = create_edit_plan(
        transcript=transcript,
        duration=probe.duration,
        remove_fillers=not args.no_fillers,
        remove_repetitions=not args.no_repetitions,
        remove_silence=not args.no_silence,
        remove_tangents=args.tangents,
    )
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(plan.to_dict(), f, indent=2)
        print(f"Saved to: {args.output}")
    else:
        print(json.dumps(plan.to_dict(), indent=2))
    
    print(f"\nOriginal: {plan.original_duration:.1f}s")
    print(f"Edited:   {plan.edited_duration:.1f}s")
    print(f"Removed:  {plan.removed_duration:.1f}s ({plan.removed_duration/plan.original_duration*100:.1f}%)")
    
    return 0


def cmd_render(args):
    """Handle render command."""
    try:
        from .render import render_video
        from .plan import EditPlan, Segment
    except ImportError:
        from render import render_video
        from plan import EditPlan, Segment
    
    # Load timeline from JSON
    with open(args.timeline) as f:
        timeline_data = json.load(f)
    
    # Build segments from timeline
    segments = []
    for seg in timeline_data.get("segments", []):
        segments.append(Segment(
            start=seg["start"],
            end=seg["end"],
            action=seg.get("action", "keep"),
            reason=seg.get("reason", ""),
            category=seg.get("category", "content"),
        ))
    
    plan = EditPlan(
        segments=segments,
        original_duration=timeline_data.get("original_duration", 0),
    )
    
    render_video(
        input_path=args.input,
        output_path=args.output,
        plan=plan,
        copy_codec=not args.reencode,
    )
    
    print(f"✓ Rendered: {args.output}")
    return 0


def cmd_edit(args):
    """Handle edit command."""
    try:
        from .pipeline import edit_video
    except ImportError:
        from pipeline import edit_video
    
    result = edit_video(
        input_path=args.input,
        output_path=args.output,
        preset=args.preset,
        remove_fillers=not args.no_fillers,
        remove_repetitions=not args.no_repetitions,
        remove_silence=not args.no_silence,
        remove_tangents=args.tangents,
        use_local_whisper=args.local,
        copy_codec=not args.reencode,
        verbose=args.verbose,
        save_artifacts=not args.no_artifacts,
    )
    
    if result.success:
        print(f"\n✓ Success! Output: {result.output_path}")
        if result.artifacts:
            print("\nArtifacts:")
            for name, path in result.artifacts.items():
                print(f"  {name}: {path}")
        return 0
    else:
        print(f"\n✗ Failed: {result.error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
