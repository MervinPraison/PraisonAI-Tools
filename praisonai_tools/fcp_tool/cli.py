"""
CLI for FCP Tool - Final Cut Pro automation commands.

Usage:
    python -m praisonai_tools.fcp_tool.cli doctor
    python -m praisonai_tools.fcp_tool.cli autoedit --instruction "..." --media /path/to/file.mov
    python -m praisonai_tools.fcp_tool.cli daemon start|stop|status
    python -m praisonai_tools.fcp_tool.cli bootstrap
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional


def main(args: Optional[list[str]] = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="praisonai-tools-fcp",
        description="Final Cut Pro automation tools",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Doctor command
    doctor_parser = subparsers.add_parser("doctor", help="Run health checks")
    doctor_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Autoedit command
    autoedit_parser = subparsers.add_parser("autoedit", help="Generate and inject FCPXML")
    autoedit_parser.add_argument(
        "--instruction", "-i", type=str, help="Editing instruction"
    )
    autoedit_parser.add_argument(
        "--instruction-file", "-f", type=str, help="File containing instruction"
    )
    autoedit_parser.add_argument(
        "--media", "-m", action="append", dest="media_paths", help="Media file path (repeatable)"
    )
    autoedit_parser.add_argument(
        "--project-name", "-n", type=str, default="Untitled Project", help="Project name"
    )
    autoedit_parser.add_argument(
        "--format", type=str, default="1080p25", help="Format preset"
    )
    autoedit_parser.add_argument(
        "--model", type=str, default="gpt-4o", help="OpenAI model"
    )
    autoedit_parser.add_argument(
        "--dry-run", action="store_true", help="Generate without injecting"
    )
    autoedit_parser.add_argument(
        "--simple", action="store_true", help="Use simple concatenation (no LLM)"
    )
    autoedit_parser.add_argument(
        "--print-intent", action="store_true", help="Print EditIntent JSON"
    )
    autoedit_parser.add_argument(
        "--print-fcpxml", action="store_true", help="Print generated FCPXML"
    )
    autoedit_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Manage injection daemon")
    daemon_parser.add_argument(
        "action", choices=["start", "stop", "status"], help="Daemon action"
    )
    daemon_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Bootstrap command
    bootstrap_parser = subparsers.add_parser(
        "bootstrap", help="One-time CommandPost setup"
    )
    bootstrap_parser.add_argument("--json", action="store_true", help="Output as JSON")

    parsed = parser.parse_args(args)

    if not parsed.command:
        parser.print_help()
        return 1

    if parsed.command == "doctor":
        return cmd_doctor(parsed)
    elif parsed.command == "autoedit":
        return cmd_autoedit(parsed)
    elif parsed.command == "daemon":
        return cmd_daemon(parsed)
    elif parsed.command == "bootstrap":
        return cmd_bootstrap(parsed)

    return 1


def cmd_doctor(args: argparse.Namespace) -> int:
    """Run health checks."""
    from .doctor import FCPDoctor

    doctor = FCPDoctor()
    results = doctor.run_all_checks()

    if args.json:
        summary = doctor.get_summary(results)
        print(json.dumps(summary, indent=2))
    else:
        doctor.print_report(results)

    return 0


def cmd_autoedit(args: argparse.Namespace) -> int:
    """Generate and inject FCPXML."""
    import os
    from .fcpxml import FCPXMLGenerator
    from .prompting import generate_edit_intent, create_simple_intent
    from .injector import Injector
    from .commandpost import CommandPostBridge

    instruction = args.instruction
    if args.instruction_file:
        with open(args.instruction_file, "r") as f:
            instruction = f.read().strip()

    media_paths = args.media_paths or []

    if not media_paths:
        print("Error: At least one --media path is required", file=sys.stderr)
        return 1

    abs_paths = [os.path.abspath(p) for p in media_paths]
    missing = [p for p in abs_paths if not os.path.exists(p)]
    if missing:
        print(f"Error: Media files not found: {missing}", file=sys.stderr)
        return 1

    try:
        if args.simple or not instruction:
            if not instruction:
                print("No instruction provided, using simple concatenation mode")
            intent = create_simple_intent(
                media_paths=abs_paths,
                project_name=args.project_name,
                format_preset=args.format,
            )
            warnings = []
        else:
            intent, warnings = generate_edit_intent(
                instruction=instruction,
                media_paths=abs_paths,
                project_name=args.project_name,
                format_preset=args.format,
                model=args.model,
            )

        if args.print_intent:
            print("\n=== EditIntent JSON ===")
            print(intent.model_dump_json(indent=2))

        generator = FCPXMLGenerator(intent)
        fcpxml = generator.generate()
        warnings.extend(generator.get_warnings())

        if args.print_fcpxml:
            print("\n=== Generated FCPXML ===")
            print(fcpxml)

        if warnings:
            print("\n=== Warnings ===")
            for w in warnings:
                print(f"  ⚠ {w}")

        if args.dry_run:
            if args.json:
                print(json.dumps({
                    "success": True,
                    "dry_run": True,
                    "intent": intent.model_dump(),
                    "fcpxml_length": len(fcpxml),
                    "warnings": warnings,
                }, indent=2))
            else:
                print("\n=== Dry Run Complete ===")
                print(f"FCPXML generated: {len(fcpxml)} characters")
                print("No injection performed (--dry-run)")
            return 0

        commandpost = CommandPostBridge()
        injector = Injector(commandpost=commandpost)

        job_id, fcpxml_path, messages = injector.inject_one_shot(
            fcpxml_content=fcpxml,
            instruction=instruction or "Simple concatenation",
            intent_json=intent.model_dump_json(),
        )

        if args.json:
            print(json.dumps({
                "success": True,
                "job_id": job_id,
                "fcpxml_path": fcpxml_path,
                "messages": messages,
                "warnings": warnings,
            }, indent=2))
        else:
            print("\n=== Injection Complete ===")
            print(f"Job ID: {job_id}")
            print(f"FCPXML: {fcpxml_path}")
            for msg in messages:
                print(f"  • {msg}")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"success": False, "error": str(e)}, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_daemon(args: argparse.Namespace) -> int:
    """Manage injection daemon."""
    from .injector import Injector

    injector = Injector()

    if args.action == "start":
        if injector.is_daemon_running():
            msg = "Daemon is already running"
            if args.json:
                print(json.dumps({"success": False, "error": msg}))
            else:
                print(msg)
            return 1

        print("Starting daemon...")
        success = injector.start_daemon(detach=True)
        if args.json:
            print(json.dumps({"success": success}))
        else:
            print("Daemon started" if success else "Failed to start daemon")
        return 0 if success else 1

    elif args.action == "stop":
        success = injector.stop_daemon()
        if args.json:
            print(json.dumps({"success": success}))
        else:
            print("Daemon stopped" if success else "Daemon not running or failed to stop")
        return 0 if success else 1

    elif args.action == "status":
        running = injector.is_daemon_running()
        state = injector.get_daemon_state()

        if args.json:
            print(json.dumps({
                "running": running,
                "state": {
                    "pid": state.pid if state else None,
                    "started_at": state.started_at if state else None,
                    "watch_folder": state.watch_folder if state else None,
                    "jobs_processed": state.jobs_processed if state else 0,
                    "last_job_at": state.last_job_at if state else None,
                } if state else None,
            }, indent=2))
        else:
            if running and state:
                print(f"Daemon running (PID: {state.pid})")
                print(f"  Started: {state.started_at}")
                print(f"  Watch folder: {state.watch_folder}")
                print(f"  Jobs processed: {state.jobs_processed}")
                if state.last_job_at:
                    print(f"  Last job: {state.last_job_at}")
            else:
                print("Daemon not running")
        return 0

    return 1


def cmd_bootstrap(args: argparse.Namespace) -> int:
    """One-time CommandPost setup."""
    from .commandpost import CommandPostBridge

    bridge = CommandPostBridge()
    results = bridge.bootstrap()

    if args.json:
        print(json.dumps({
            "results": [{"success": s, "message": m} for s, m in results],
            "all_success": all(s for s, _ in results),
        }, indent=2))
    else:
        print("\n=== CommandPost Bootstrap ===")
        for success, message in results:
            status = "✓" if success else "✗"
            print(f"  {status} {message}")
        print()
        if all(s for s, _ in results):
            print("Bootstrap complete!")
        else:
            print("Some steps failed. See above for details.")

    return 0 if all(s for s, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
