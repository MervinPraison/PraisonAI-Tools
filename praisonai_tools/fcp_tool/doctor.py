"""
FCP Doctor - Health Checks for Final Cut Pro Integration

Provides diagnostic checks and remediation guidance for the FCP integration.
"""

from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass
from typing import Optional

from .commandpost import CommandPostBridge


@dataclass
class CheckResult:
    """Result of a health check."""
    name: str
    passed: bool
    message: str
    remediation: Optional[str] = None


class FCPDoctor:
    """
    Diagnostic tool for FCP integration health checks.
    
    Checks for:
    - macOS environment
    - Final Cut Pro installation
    - CommandPost installation
    - cmdpost CLI availability
    - Watch folder configuration
    """

    def __init__(self, commandpost: Optional[CommandPostBridge] = None):
        """
        Initialize the doctor.
        
        Args:
            commandpost: CommandPost bridge instance
        """
        self.commandpost = commandpost or CommandPostBridge()

    def run_all_checks(self) -> list[CheckResult]:
        """Run all health checks."""
        return [
            self.check_macos(),
            self.check_final_cut_pro(),
            self.check_commandpost_app(),
            self.check_cmdpost_cli(),
            self.check_watch_folder(),
            self.check_auto_import(),
            self.check_openai_api_key(),
        ]

    def check_macos(self) -> CheckResult:
        """Check if running on macOS."""
        is_macos = platform.system() == "Darwin"
        if is_macos:
            version = platform.mac_ver()[0]
            return CheckResult(
                name="macOS",
                passed=True,
                message=f"Running on macOS {version}",
            )
        else:
            return CheckResult(
                name="macOS",
                passed=False,
                message=f"Running on {platform.system()}, not macOS",
                remediation="FCP integration requires macOS. Other platforms can generate FCPXML but cannot auto-import.",
            )

    def check_final_cut_pro(self) -> CheckResult:
        """Check if Final Cut Pro is installed."""
        fcp_paths = [
            "/Applications/Final Cut Pro.app",
            os.path.expanduser("~/Applications/Final Cut Pro.app"),
        ]

        for path in fcp_paths:
            if os.path.isdir(path):
                return CheckResult(
                    name="Final Cut Pro",
                    passed=True,
                    message=f"Found at {path}",
                )

        return CheckResult(
            name="Final Cut Pro",
            passed=False,
            message="Final Cut Pro not found",
            remediation="Install Final Cut Pro from the Mac App Store.",
        )

    def check_commandpost_app(self) -> CheckResult:
        """Check if CommandPost app is installed."""
        cp_paths = [
            "/Applications/CommandPost.app",
            os.path.expanduser("~/Applications/CommandPost.app"),
        ]

        for path in cp_paths:
            if os.path.isdir(path):
                return CheckResult(
                    name="CommandPost App",
                    passed=True,
                    message=f"Found at {path}",
                )

        return CheckResult(
            name="CommandPost App",
            passed=False,
            message="CommandPost not found",
            remediation="Download CommandPost from https://commandpost.io",
        )

    def check_cmdpost_cli(self) -> CheckResult:
        """Check if cmdpost CLI is available."""
        cmdpost_path = self.commandpost.cmdpost_path

        if cmdpost_path:
            return CheckResult(
                name="cmdpost CLI",
                passed=True,
                message=f"Found at {cmdpost_path}",
            )

        cmdpost_in_path = shutil.which("cmdpost")
        if cmdpost_in_path:
            return CheckResult(
                name="cmdpost CLI",
                passed=True,
                message=f"Found in PATH at {cmdpost_in_path}",
            )

        return CheckResult(
            name="cmdpost CLI",
            passed=False,
            message="cmdpost CLI not found",
            remediation=(
                "Ensure CommandPost is installed and running. "
                "The cmdpost CLI is bundled with CommandPost at: "
                "/Applications/CommandPost.app/Contents/Resources/extensions/hs/cmdpost"
            ),
        )

    def check_watch_folder(self) -> CheckResult:
        """Check if watch folder exists."""
        watch_folder = self.commandpost.watch_folder

        if os.path.isdir(watch_folder):
            return CheckResult(
                name="Watch Folder",
                passed=True,
                message=f"Exists at {watch_folder}",
            )

        return CheckResult(
            name="Watch Folder",
            passed=False,
            message=f"Watch folder not found: {watch_folder}",
            remediation=f"Run: mkdir -p {watch_folder}",
        )

    def check_auto_import(self) -> CheckResult:
        """Check if auto-import is enabled in CommandPost."""
        status = self.commandpost.get_status()

        if not status.cmdpost_available:
            return CheckResult(
                name="Auto-Import",
                passed=False,
                message="Cannot check - cmdpost CLI not available",
                remediation="Install and run CommandPost first.",
            )

        if status.auto_import_enabled:
            return CheckResult(
                name="Auto-Import",
                passed=True,
                message="Enabled in CommandPost",
            )

        return CheckResult(
            name="Auto-Import",
            passed=False,
            message="Auto-import not enabled or could not be verified",
            remediation=(
                "Run: praisonai-tools fcp bootstrap\n"
                "Or manually enable in CommandPost preferences."
            ),
        )

    def check_openai_api_key(self) -> CheckResult:
        """Check if OpenAI API key is configured."""
        api_key = os.environ.get("OPENAI_API_KEY")

        if api_key:
            masked = f"...{api_key[-4:]}" if len(api_key) > 4 else "****"
            return CheckResult(
                name="OpenAI API Key",
                passed=True,
                message=f"Set (ending in {masked})",
            )

        return CheckResult(
            name="OpenAI API Key",
            passed=False,
            message="OPENAI_API_KEY not set",
            remediation="Set with: export OPENAI_API_KEY=your-key",
        )

    def print_report(self, results: Optional[list[CheckResult]] = None) -> bool:
        """
        Print a formatted health check report.
        
        Args:
            results: Check results (runs all checks if not provided)
            
        Returns:
            True if all checks passed
        """
        if results is None:
            results = self.run_all_checks()

        print("\n" + "=" * 60)
        print("FCP Integration Health Check")
        print("=" * 60 + "\n")

        all_passed = True
        for result in results:
            status = "✓" if result.passed else "✗"
            print(f"  {status} {result.name}: {result.message}")
            if not result.passed:
                all_passed = False
                if result.remediation:
                    print(f"    → {result.remediation}")
            print()

        print("=" * 60)
        if all_passed:
            print("All checks passed! FCP integration is ready.")
        else:
            print("Some checks failed. See remediation steps above.")
        print("=" * 60 + "\n")

        return all_passed

    def get_summary(self, results: Optional[list[CheckResult]] = None) -> dict:
        """
        Get a summary of health check results.
        
        Args:
            results: Check results (runs all checks if not provided)
            
        Returns:
            Summary dictionary
        """
        if results is None:
            results = self.run_all_checks()

        passed = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed]

        return {
            "total": len(results),
            "passed": len(passed),
            "failed": len(failed),
            "all_passed": len(failed) == 0,
            "checks": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "remediation": r.remediation,
                }
                for r in results
            ],
        }
