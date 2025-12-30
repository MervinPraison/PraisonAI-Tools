"""
FCPXML Injector for Final Cut Pro Integration

Manages watch folder delivery and daemon mode for automatic FCPXML injection.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from .commandpost import CommandPostBridge


class JobStatus(str, Enum):
    """Job processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    INJECTED = "injected"
    FAILED = "failed"


@dataclass
class InjectionJob:
    """Represents an FCPXML injection job."""
    job_id: str
    created_at: str
    instruction: str
    intent_path: Optional[str] = None
    fcpxml_path: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    error: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "InjectionJob":
        """Create from dictionary."""
        d = d.copy()
        d["status"] = JobStatus(d["status"])
        return cls(**d)


@dataclass
class DaemonState:
    """State of the daemon process."""
    pid: int
    started_at: str
    watch_folder: str
    jobs_processed: int = 0
    last_job_at: Optional[str] = None


class Injector:
    """
    Manages FCPXML injection into Final Cut Pro via CommandPost.
    
    Supports both one-shot injection and daemon mode with watch folder.
    """

    DEFAULT_BASE_DIR = os.path.expanduser("~/.praison/fcp")

    def __init__(
        self,
        base_dir: Optional[str] = None,
        watch_folder: Optional[str] = None,
        commandpost: Optional[CommandPostBridge] = None,
    ):
        """
        Initialize the injector.
        
        Args:
            base_dir: Base directory for jobs and outputs
            watch_folder: Watch folder for CommandPost
            commandpost: CommandPost bridge instance
        """
        self.base_dir = Path(base_dir or self.DEFAULT_BASE_DIR)
        self.jobs_dir = self.base_dir / "jobs"
        self.out_dir = self.base_dir / "out"
        self.watch_folder = Path(watch_folder or self.base_dir / "watch" / "fcpxml")
        self.pid_file = self.base_dir / "daemon.pid"
        self.state_file = self.base_dir / "daemon.state"

        self.commandpost = commandpost or CommandPostBridge(
            watch_folder=str(self.watch_folder)
        )

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create necessary directories."""
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.watch_folder.mkdir(parents=True, exist_ok=True)

    def inject_one_shot(
        self,
        fcpxml_content: str,
        job_id: Optional[str] = None,
        instruction: str = "",
        intent_json: Optional[str] = None,
        delete_after_import: bool = False,
    ) -> tuple[str, str, list[str]]:
        """
        Perform one-shot FCPXML injection.
        
        Args:
            fcpxml_content: FCPXML content to inject
            job_id: Optional job ID (generated if not provided)
            instruction: Original instruction for logging
            intent_json: Optional EditIntent JSON for logging
            delete_after_import: Whether to delete file after import
            
        Returns:
            Tuple of (job_id, fcpxml_path, messages)
        """
        job_id = job_id or str(uuid.uuid4())
        messages = []

        job = InjectionJob(
            job_id=job_id,
            created_at=datetime.utcnow().isoformat(),
            instruction=instruction,
        )

        if intent_json:
            intent_path = self.jobs_dir / f"{job_id}_intent.json"
            intent_path.write_text(intent_json)
            job.intent_path = str(intent_path)
            messages.append(f"Intent saved: {intent_path}")

        fcpxml_path = self._write_fcpxml_atomic(fcpxml_content, job_id)
        job.fcpxml_path = str(fcpxml_path)
        messages.append(f"FCPXML written: {fcpxml_path}")

        watch_path = self._deliver_to_watch_folder(fcpxml_path, job_id)
        messages.append(f"Delivered to watch folder: {watch_path}")

        job.status = JobStatus.INJECTED
        job.completed_at = datetime.utcnow().isoformat()

        job_path = self.jobs_dir / f"{job_id}.json"
        job_path.write_text(json.dumps(job.to_dict(), indent=2))
        messages.append(f"Job logged: {job_path}")

        if delete_after_import:
            try:
                os.remove(fcpxml_path)
                messages.append(f"Cleaned up: {fcpxml_path}")
            except OSError:
                pass

        return job_id, str(watch_path), messages

    def _write_fcpxml_atomic(self, content: str, job_id: str) -> Path:
        """
        Write FCPXML content atomically (write to temp, then rename).
        
        Args:
            content: FCPXML content
            job_id: Job ID for filename
            
        Returns:
            Path to the written file
        """
        final_path = self.out_dir / f"{job_id}.fcpxml"

        fd, tmp_path = tempfile.mkstemp(
            suffix=".fcpxml.tmp",
            dir=str(self.out_dir),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.rename(tmp_path, final_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

        return final_path

    def _deliver_to_watch_folder(self, source_path: Path, job_id: str) -> Path:
        """
        Deliver FCPXML to the watch folder with atomic rename.
        
        Args:
            source_path: Source FCPXML file
            job_id: Job ID for filename
            
        Returns:
            Path in watch folder
        """
        watch_path = self.watch_folder / f"{job_id}.fcpxml"

        fd, tmp_path = tempfile.mkstemp(
            suffix=".fcpxml.tmp",
            dir=str(self.watch_folder),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(source_path.read_text())
            os.rename(tmp_path, watch_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

        return watch_path

    def get_job(self, job_id: str) -> Optional[InjectionJob]:
        """Get a job by ID."""
        job_path = self.jobs_dir / f"{job_id}.json"
        if not job_path.exists():
            return None
        try:
            return InjectionJob.from_dict(json.loads(job_path.read_text()))
        except (json.JSONDecodeError, KeyError):
            return None

    def list_jobs(self, limit: int = 10) -> list[InjectionJob]:
        """List recent jobs."""
        jobs = []
        for job_file in sorted(
            self.jobs_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]:
            if "_intent" not in job_file.name:
                try:
                    jobs.append(InjectionJob.from_dict(json.loads(job_file.read_text())))
                except (json.JSONDecodeError, KeyError):
                    pass
        return jobs

    def is_daemon_running(self) -> bool:
        """Check if daemon is running."""
        if not self.pid_file.exists():
            return False

        try:
            pid = int(self.pid_file.read_text().strip())
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            return False

    def get_daemon_state(self) -> Optional[DaemonState]:
        """Get daemon state if running."""
        if not self.is_daemon_running():
            return None

        if not self.state_file.exists():
            return None

        try:
            data = json.loads(self.state_file.read_text())
            return DaemonState(**data)
        except (json.JSONDecodeError, TypeError):
            return None

    def start_daemon(
        self,
        detach: bool = False,
        poll_interval: float = 1.0,
        on_job: Optional[Callable[[InjectionJob], None]] = None,
    ) -> bool:
        """
        Start the daemon process.
        
        Args:
            detach: Whether to detach from terminal
            poll_interval: Seconds between poll cycles
            on_job: Callback when job is processed
            
        Returns:
            True if started successfully
        """
        if self.is_daemon_running():
            return False

        if detach:
            pid = os.fork()
            if pid > 0:
                return True
            os.setsid()
            pid = os.fork()
            if pid > 0:
                sys.exit(0)

        self.pid_file.write_text(str(os.getpid()))

        state = DaemonState(
            pid=os.getpid(),
            started_at=datetime.utcnow().isoformat(),
            watch_folder=str(self.watch_folder),
        )
        self.state_file.write_text(json.dumps(asdict(state)))

        self._running = True

        def handle_signal(signum, frame):
            self._running = False

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

        try:
            self._daemon_loop(poll_interval, on_job, state)
        finally:
            self._cleanup_daemon()

        return True

    def _daemon_loop(
        self,
        poll_interval: float,
        on_job: Optional[Callable[[InjectionJob], None]],
        state: DaemonState,
    ) -> None:
        """Main daemon loop."""
        pending_dir = self.base_dir / "pending"
        pending_dir.mkdir(exist_ok=True)

        while self._running:
            for pending_file in pending_dir.glob("*.json"):
                try:
                    job_data = json.loads(pending_file.read_text())
                    job = InjectionJob.from_dict(job_data)

                    if job.fcpxml_path and os.path.exists(job.fcpxml_path):
                        self._deliver_to_watch_folder(
                            Path(job.fcpxml_path),
                            job.job_id,
                        )
                        job.status = JobStatus.INJECTED
                        job.completed_at = datetime.utcnow().isoformat()
                    else:
                        job.status = JobStatus.FAILED
                        job.error = "FCPXML file not found"

                    job_path = self.jobs_dir / f"{job.job_id}.json"
                    job_path.write_text(json.dumps(job.to_dict(), indent=2))

                    pending_file.unlink()

                    state.jobs_processed += 1
                    state.last_job_at = datetime.utcnow().isoformat()
                    self.state_file.write_text(json.dumps(asdict(state)))

                    if on_job:
                        on_job(job)

                except Exception as e:
                    try:
                        error_path = pending_dir / f"{pending_file.stem}_error.txt"
                        error_path.write_text(str(e))
                        pending_file.unlink()
                    except Exception:
                        pass

            time.sleep(poll_interval)

    def _cleanup_daemon(self) -> None:
        """Clean up daemon files."""
        try:
            self.pid_file.unlink(missing_ok=True)
        except Exception:
            pass

    def stop_daemon(self) -> bool:
        """
        Stop the daemon process.
        
        Returns:
            True if stopped successfully
        """
        if not self.pid_file.exists():
            return False

        try:
            pid = int(self.pid_file.read_text().strip())
            os.kill(pid, signal.SIGTERM)

            for _ in range(50):
                time.sleep(0.1)
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break

            self.pid_file.unlink(missing_ok=True)
            return True

        except (ValueError, ProcessLookupError, PermissionError):
            self.pid_file.unlink(missing_ok=True)
            return False

    def submit_job(
        self,
        fcpxml_content: str,
        instruction: str = "",
        intent_json: Optional[str] = None,
    ) -> str:
        """
        Submit a job to the daemon queue.
        
        Args:
            fcpxml_content: FCPXML content
            instruction: Original instruction
            intent_json: Optional EditIntent JSON
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())

        fcpxml_path = self._write_fcpxml_atomic(fcpxml_content, job_id)

        job = InjectionJob(
            job_id=job_id,
            created_at=datetime.utcnow().isoformat(),
            instruction=instruction,
            fcpxml_path=str(fcpxml_path),
        )

        if intent_json:
            intent_path = self.jobs_dir / f"{job_id}_intent.json"
            intent_path.write_text(intent_json)
            job.intent_path = str(intent_path)

        pending_dir = self.base_dir / "pending"
        pending_dir.mkdir(exist_ok=True)

        pending_path = pending_dir / f"{job_id}.json"
        pending_path.write_text(json.dumps(job.to_dict(), indent=2))

        return job_id
