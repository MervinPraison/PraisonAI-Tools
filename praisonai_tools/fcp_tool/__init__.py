"""
FCP Tool - Final Cut Pro automation tools for Agent Recipes.

This module provides tools for:
- EditIntent schema validation and generation
- FCPXML generation from EditIntent
- CommandPost integration for auto-import
- Injection daemon for batch processing
- Health checks and diagnostics

Usage:
    from praisonai_tools.fcp_tool import (
        fcp_autoedit,
        fcp_doctor,
        EditIntent,
        FCPXMLGenerator,
    )
"""

from .intent import (
    EditIntent,
    Asset,
    Segment,
    Marker,
    Timeline,
    Project,
    ProjectFormat,
    AudioSettings,
    AudioRole,
    AudioLayout,
    Operations,
    seconds_to_rational,
    rational_to_seconds,
    get_format_preset,
    FORMAT_PRESETS,
)
from .fcpxml import FCPXMLGenerator, generate_fcpxml, validate_fcpxml_structure
from .commandpost import CommandPostBridge, CommandPostStatus
from .injector import Injector, InjectionJob, JobStatus, DaemonState
from .doctor import FCPDoctor, CheckResult
from .prompting import generate_edit_intent, create_simple_intent

__all__ = [
    # Intent schema
    "EditIntent",
    "Asset",
    "Segment",
    "Marker",
    "Timeline",
    "Project",
    "ProjectFormat",
    "AudioSettings",
    "AudioRole",
    "AudioLayout",
    "Operations",
    "seconds_to_rational",
    "rational_to_seconds",
    "get_format_preset",
    "FORMAT_PRESETS",
    # FCPXML
    "FCPXMLGenerator",
    "generate_fcpxml",
    "validate_fcpxml_structure",
    # CommandPost
    "CommandPostBridge",
    "CommandPostStatus",
    # Injector
    "Injector",
    "InjectionJob",
    "JobStatus",
    "DaemonState",
    # Doctor
    "FCPDoctor",
    "CheckResult",
    # Prompting
    "generate_edit_intent",
    "create_simple_intent",
]


def fcp_doctor() -> dict:
    """
    Run health checks for FCP integration.
    
    Returns:
        dict: Health check results with 'all_passed' boolean and 'checks' list
    """
    doctor = FCPDoctor()
    results = doctor.run_all_checks()
    summary = doctor.get_summary(results)
    return {
        "success": True,
        "all_passed": summary["all_passed"],
        "passed": summary["passed"],
        "failed": summary["failed"],
        "checks": summary["checks"],
    }


def fcp_autoedit(
    action: str,
    instruction: str = None,
    media_paths: list = None,
    project_name: str = "AI Generated Project",
    format_preset: str = "1080p25",
    intent_json: str = None,
    fcpxml_content: str = None,
    watch_folder: str = None,
    dry_run: bool = False,
    model: str = "gpt-4o",
) -> dict:
    """
    FCP AutoEdit tool for generating and injecting FCPXML.
    
    Actions:
    - "generate_intent": Generate EditIntent from instruction
    - "generate_fcpxml": Generate FCPXML from EditIntent
    - "inject": Inject FCPXML into Final Cut Pro
    - "full_pipeline": Run the complete pipeline
    
    Args:
        action: The action to perform
        instruction: Natural language editing instruction
        media_paths: List of media file paths
        project_name: Project name
        format_preset: Format preset (e.g., "1080p25")
        intent_json: EditIntent JSON string (for generate_fcpxml)
        fcpxml_content: FCPXML content (for inject)
        watch_folder: Watch folder path
        dry_run: If True, don't inject into FCP
        model: OpenAI model to use
        
    Returns:
        dict: Result with success status and relevant data
    """
    import json
    import os
    
    if action == "generate_intent":
        if not instruction:
            return {"success": False, "error": "instruction is required"}
        if not media_paths:
            return {"success": False, "error": "media_paths is required"}
        
        abs_paths = [os.path.abspath(p) for p in media_paths]
        missing = [p for p in abs_paths if not os.path.exists(p)]
        if missing:
            return {"success": False, "error": f"Media files not found: {missing}"}
        
        intent, warnings = generate_edit_intent(
            instruction=instruction,
            media_paths=abs_paths,
            project_name=project_name,
            format_preset=format_preset,
            model=model,
        )
        
        return {
            "success": True,
            "intent_json": intent.model_dump_json(),
            "intent": intent.model_dump(),
            "warnings": warnings,
            "assets_count": len(intent.assets),
            "segments_count": len(intent.timeline.segments),
        }
    
    elif action == "generate_fcpxml":
        if not intent_json:
            return {"success": False, "error": "intent_json is required"}
        
        try:
            intent_data = json.loads(intent_json)
            intent = EditIntent.model_validate(intent_data)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Invalid EditIntent: {e}"}
        
        generator = FCPXMLGenerator(intent)
        fcpxml = generator.generate()
        warnings = generator.get_warnings()
        
        return {
            "success": True,
            "fcpxml": fcpxml,
            "fcpxml_length": len(fcpxml),
            "warnings": warnings,
        }
    
    elif action == "inject":
        if not fcpxml_content:
            return {"success": False, "error": "fcpxml_content is required"}
        
        commandpost = CommandPostBridge(watch_folder=watch_folder)
        injector = Injector(watch_folder=watch_folder, commandpost=commandpost)
        
        job_id, fcpxml_path, messages = injector.inject_one_shot(
            fcpxml_content=fcpxml_content,
            instruction=instruction or "",
            intent_json=intent_json,
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "fcpxml_path": fcpxml_path,
            "messages": messages,
        }
    
    elif action == "full_pipeline":
        # Generate intent
        intent_result = fcp_autoedit(
            action="generate_intent",
            instruction=instruction,
            media_paths=media_paths,
            project_name=project_name,
            format_preset=format_preset,
            model=model,
        )
        if not intent_result["success"]:
            return intent_result
        
        # Generate FCPXML
        fcpxml_result = fcp_autoedit(
            action="generate_fcpxml",
            intent_json=intent_result["intent_json"],
        )
        if not fcpxml_result["success"]:
            return fcpxml_result
        
        all_warnings = intent_result.get("warnings", []) + fcpxml_result.get("warnings", [])
        
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "intent": intent_result["intent"],
                "fcpxml_length": fcpxml_result["fcpxml_length"],
                "warnings": all_warnings,
            }
        
        # Inject
        inject_result = fcp_autoedit(
            action="inject",
            fcpxml_content=fcpxml_result["fcpxml"],
            instruction=instruction,
            intent_json=intent_result["intent_json"],
            watch_folder=watch_folder,
        )
        if not inject_result["success"]:
            return inject_result
        
        return {
            "success": True,
            "job_id": inject_result["job_id"],
            "fcpxml_path": inject_result["fcpxml_path"],
            "assets_count": intent_result["assets_count"],
            "segments_count": intent_result["segments_count"],
            "warnings": all_warnings,
            "messages": inject_result["messages"],
        }
    
    else:
        return {
            "success": False,
            "error": f"Unknown action: {action}. Valid: generate_intent, generate_fcpxml, inject, full_pipeline",
        }
