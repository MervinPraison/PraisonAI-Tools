"""
CommandPost Bridge for Final Cut Pro Integration

Interfaces with CommandPost's cmdpost CLI to configure watch folders
and trigger FCPXML auto-import into Final Cut Pro.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CommandPostStatus:
    """Status of CommandPost installation and configuration."""
    is_macos: bool
    commandpost_installed: bool
    cmdpost_available: bool
    cmdpost_path: Optional[str]
    watch_folder_configured: bool
    watch_folder_path: Optional[str]
    auto_import_enabled: bool
    errors: list[str]

    @property
    def is_ready(self) -> bool:
        """Check if CommandPost is ready for auto-import."""
        return (
            self.is_macos
            and self.commandpost_installed
            and self.cmdpost_available
            and self.watch_folder_configured
            and self.auto_import_enabled
        )


class CommandPostBridge:
    """
    Bridge to CommandPost for FCPXML auto-import.
    
    CommandPost is a macOS app that extends Final Cut Pro with automation
    capabilities. This bridge uses the cmdpost CLI to configure watch folders
    and enable automatic FCPXML import.
    """

    KNOWN_CMDPOST_PATHS = [
        "/Applications/CommandPost.app/Contents/Resources/extensions/hs/cmdpost",
        "/usr/local/bin/cmdpost",
        os.path.expanduser("~/Applications/CommandPost.app/Contents/Resources/extensions/hs/cmdpost"),
    ]

    COMMANDPOST_APP_PATHS = [
        "/Applications/CommandPost.app",
        os.path.expanduser("~/Applications/CommandPost.app"),
    ]

    DEFAULT_WATCH_FOLDER = os.path.expanduser("~/.praison/fcp/watch/fcpxml")

    def __init__(self, cmdpost_path: Optional[str] = None, watch_folder: Optional[str] = None):
        """
        Initialize the CommandPost bridge.
        
        Args:
            cmdpost_path: Path to cmdpost CLI (auto-detected if not provided)
            watch_folder: Watch folder path (uses default if not provided)
        """
        self.cmdpost_path = cmdpost_path or self._find_cmdpost()
        self.watch_folder = watch_folder or self.DEFAULT_WATCH_FOLDER

    def _find_cmdpost(self) -> Optional[str]:
        """Find the cmdpost CLI binary."""
        cmdpost_in_path = shutil.which("cmdpost")
        if cmdpost_in_path:
            return cmdpost_in_path

        for path in self.KNOWN_CMDPOST_PATHS:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        return None

    def _is_commandpost_installed(self) -> bool:
        """Check if CommandPost app is installed."""
        for path in self.COMMANDPOST_APP_PATHS:
            if os.path.isdir(path):
                return True
        return False

    def get_status(self) -> CommandPostStatus:
        """Get the current status of CommandPost configuration."""
        is_macos = platform.system() == "Darwin"
        errors = []

        if not is_macos:
            errors.append("CommandPost is only available on macOS")
            return CommandPostStatus(
                is_macos=False,
                commandpost_installed=False,
                cmdpost_available=False,
                cmdpost_path=None,
                watch_folder_configured=False,
                watch_folder_path=None,
                auto_import_enabled=False,
                errors=errors,
            )

        commandpost_installed = self._is_commandpost_installed()
        if not commandpost_installed:
            errors.append("CommandPost is not installed. Download from https://commandpost.io")

        cmdpost_available = self.cmdpost_path is not None
        if not cmdpost_available:
            errors.append("cmdpost CLI not found. Ensure CommandPost is installed and running.")

        watch_folder_configured = os.path.isdir(self.watch_folder)
        auto_import_enabled = False

        if cmdpost_available and watch_folder_configured:
            auto_import_enabled = self._check_auto_import_enabled()

        return CommandPostStatus(
            is_macos=is_macos,
            commandpost_installed=commandpost_installed,
            cmdpost_available=cmdpost_available,
            cmdpost_path=self.cmdpost_path,
            watch_folder_configured=watch_folder_configured,
            watch_folder_path=self.watch_folder if watch_folder_configured else None,
            auto_import_enabled=auto_import_enabled,
            errors=errors,
        )

    def _check_auto_import_enabled(self) -> bool:
        """Check if auto-import is enabled in CommandPost."""
        if not self.cmdpost_path:
            return False

        lua_script = '''
local fcpxmlPlugin = require("cp.plugins")("finalcutpro.watchfolders.fcpxml")
if fcpxmlPlugin and fcpxmlPlugin.automaticallyImport then
    print(fcpxmlPlugin.automaticallyImport() and "true" or "false")
else
    print("unknown")
end
'''
        try:
            result = subprocess.run(
                [self.cmdpost_path, "-c", lua_script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() == "true"
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False

    def setup_watch_folder(self) -> tuple[bool, str]:
        """
        Set up the watch folder for FCPXML auto-import.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            Path(self.watch_folder).mkdir(parents=True, exist_ok=True)
            return True, f"Watch folder created: {self.watch_folder}"
        except OSError as e:
            return False, f"Failed to create watch folder: {e}"

    def configure_auto_import(self, enable: bool = True) -> tuple[bool, str]:
        """
        Configure CommandPost to automatically import FCPXML files.
        
        Args:
            enable: Whether to enable auto-import
            
        Returns:
            Tuple of (success, message)
        """
        if not self.cmdpost_path:
            return False, "cmdpost CLI not available"

        lua_script = f'''
local fcpxmlPlugin = require("cp.plugins")("finalcutpro.watchfolders.fcpxml")
if fcpxmlPlugin and fcpxmlPlugin.automaticallyImport then
    fcpxmlPlugin.automaticallyImport({"true" if enable else "false"})
    print("configured")
else
    print("plugin_not_found")
end
'''
        try:
            result = subprocess.run(
                [self.cmdpost_path, "-c", lua_script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if "configured" in result.stdout:
                return True, f"Auto-import {'enabled' if enable else 'disabled'}"
            elif "plugin_not_found" in result.stdout:
                return False, "FCPXML watch folder plugin not found in CommandPost"
            else:
                return False, f"Unexpected response: {result.stdout}"
        except subprocess.TimeoutExpired:
            return False, "CommandPost command timed out"
        except subprocess.SubprocessError as e:
            return False, f"Failed to configure CommandPost: {e}"

    def add_watch_folder(self) -> tuple[bool, str]:
        """
        Add the watch folder to CommandPost's FCPXML watch list.
        
        Returns:
            Tuple of (success, message)
        """
        if not self.cmdpost_path:
            return False, "cmdpost CLI not available"

        escaped_path = self.watch_folder.replace('"', '\\"')
        lua_script = f'''
local fcpxmlPlugin = require("cp.plugins")("finalcutpro.watchfolders.fcpxml")
if fcpxmlPlugin and fcpxmlPlugin.addWatchFolder then
    fcpxmlPlugin.addWatchFolder("{escaped_path}")
    print("added")
elseif fcpxmlPlugin then
    -- Try alternative method
    local watchFolders = fcpxmlPlugin.watchFolders
    if watchFolders and watchFolders.addFolder then
        watchFolders.addFolder("{escaped_path}")
        print("added")
    else
        print("method_not_found")
    end
else
    print("plugin_not_found")
end
'''
        try:
            result = subprocess.run(
                [self.cmdpost_path, "-c", lua_script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if "added" in result.stdout:
                return True, f"Watch folder added: {self.watch_folder}"
            elif "method_not_found" in result.stdout:
                return False, (
                    "Watch folder API not available. "
                    "Please add the watch folder manually in CommandPost preferences."
                )
            elif "plugin_not_found" in result.stdout:
                return False, "FCPXML watch folder plugin not found in CommandPost"
            else:
                return False, f"Unexpected response: {result.stdout}"
        except subprocess.TimeoutExpired:
            return False, "CommandPost command timed out"
        except subprocess.SubprocessError as e:
            return False, f"Failed to add watch folder: {e}"

    def trigger_import(self, fcpxml_path: str) -> tuple[bool, str]:
        """
        Trigger import of a specific FCPXML file.
        
        This is an alternative to watch folder auto-import that directly
        calls CommandPost to import a file.
        
        Args:
            fcpxml_path: Path to the FCPXML file
            
        Returns:
            Tuple of (success, message)
        """
        if not self.cmdpost_path:
            return False, "cmdpost CLI not available"

        if not os.path.isfile(fcpxml_path):
            return False, f"FCPXML file not found: {fcpxml_path}"

        escaped_path = fcpxml_path.replace('"', '\\"')
        lua_script = f'''
local fcpxmlPlugin = require("cp.plugins")("finalcutpro.watchfolders.fcpxml")
if fcpxmlPlugin and fcpxmlPlugin.insertFilesIntoFinalCutPro then
    fcpxmlPlugin.insertFilesIntoFinalCutPro({{"{escaped_path}"}})
    print("imported")
elseif fcpxmlPlugin and fcpxmlPlugin.importFile then
    fcpxmlPlugin.importFile("{escaped_path}")
    print("imported")
else
    print("import_not_available")
end
'''
        try:
            result = subprocess.run(
                [self.cmdpost_path, "-c", lua_script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if "imported" in result.stdout:
                return True, f"FCPXML imported: {fcpxml_path}"
            elif "import_not_available" in result.stdout:
                return False, (
                    "Direct import not available. "
                    "File will be imported via watch folder if configured."
                )
            else:
                return False, f"Import may have failed: {result.stdout}"
        except subprocess.TimeoutExpired:
            return False, "Import command timed out"
        except subprocess.SubprocessError as e:
            return False, f"Failed to import: {e}"

    def bring_fcp_to_front(self) -> tuple[bool, str]:
        """
        Bring Final Cut Pro to the foreground.
        
        Returns:
            Tuple of (success, message)
        """
        if platform.system() != "Darwin":
            return False, "Only available on macOS"

        try:
            subprocess.run(
                ["osascript", "-e", 'tell application "Final Cut Pro" to activate'],
                capture_output=True,
                timeout=5,
            )
            return True, "Final Cut Pro activated"
        except subprocess.SubprocessError as e:
            return False, f"Failed to activate Final Cut Pro: {e}"

    def bootstrap(self) -> list[tuple[bool, str]]:
        """
        Perform one-time bootstrap setup for CommandPost integration.
        
        Returns:
            List of (success, message) tuples for each setup step
        """
        results = []

        success, msg = self.setup_watch_folder()
        results.append((success, msg))

        if self.cmdpost_path:
            success, msg = self.configure_auto_import(True)
            results.append((success, msg))

            success, msg = self.add_watch_folder()
            results.append((success, msg))
        else:
            results.append((False, "cmdpost CLI not available - skipping configuration"))

        return results
