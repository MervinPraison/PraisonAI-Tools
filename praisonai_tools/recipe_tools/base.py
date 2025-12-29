"""
Base classes for Recipe Tools.

Provides common infrastructure for all recipe tools including:
- Structured result types
- Dependency checking
- Logging
- Error handling
"""

import logging
import subprocess
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class DependencyError(Exception):
    """Raised when a required dependency is missing."""
    
    def __init__(self, dependency: str, install_hint: str = ""):
        self.dependency = dependency
        self.install_hint = install_hint
        message = f"Missing dependency: {dependency}"
        if install_hint:
            message += f". Install with: {install_hint}"
        super().__init__(message)


@dataclass
class RecipeToolResult:
    """Base result class for recipe tool operations."""
    success: bool
    message: str = ""
    data: Any = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings,
            "duration_seconds": self.duration_seconds,
        }


class RecipeToolBase(ABC):
    """
    Base class for all recipe tools.
    
    Subclasses must implement:
    - name: Tool name
    - description: Tool description
    - check_dependencies(): Verify required binaries/libraries
    """
    
    name: str = "base_tool"
    description: str = "Base recipe tool"
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._logger = logging.getLogger(f"{__name__}.{self.name}")
        if verbose:
            self._logger.setLevel(logging.DEBUG)
    
    @abstractmethod
    def check_dependencies(self) -> Dict[str, bool]:
        """
        Check if required dependencies are available.
        
        Returns:
            Dict mapping dependency name to availability status
        """
        pass
    
    def require_dependencies(self, deps: List[str]) -> None:
        """
        Raise DependencyError if any required dependencies are missing.
        
        Args:
            deps: List of dependency names to check
        """
        status = self.check_dependencies()
        missing = [d for d in deps if not status.get(d, False)]
        if missing:
            raise DependencyError(
                ", ".join(missing),
                self._get_install_hint(missing[0])
            )
    
    def _get_install_hint(self, dep: str) -> str:
        """Get installation hint for a dependency."""
        hints = {
            "ffmpeg": "brew install ffmpeg (macOS) or apt install ffmpeg (Linux)",
            "ffprobe": "brew install ffmpeg (macOS) or apt install ffmpeg (Linux)",
            "pdftotext": "brew install poppler (macOS) or apt install poppler-utils (Linux)",
            "pdfinfo": "brew install poppler (macOS) or apt install poppler-utils (Linux)",
            "pdfimages": "brew install poppler (macOS) or apt install poppler-utils (Linux)",
            "pandoc": "brew install pandoc (macOS) or apt install pandoc (Linux)",
            "convert": "brew install imagemagick (macOS) or apt install imagemagick (Linux)",
            "montage": "brew install imagemagick (macOS) or apt install imagemagick (Linux)",
            "git": "brew install git (macOS) or apt install git (Linux)",
            "tesseract": "brew install tesseract (macOS) or apt install tesseract-ocr (Linux)",
        }
        return hints.get(dep, f"pip install {dep}")
    
    def _check_binary(self, name: str) -> bool:
        """Check if a binary is available in PATH."""
        return shutil.which(name) is not None
    
    def _run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        capture_output: bool = True,
        timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess:
        """
        Run a shell command safely.
        
        Args:
            cmd: Command and arguments
            cwd: Working directory
            capture_output: Whether to capture stdout/stderr
            timeout: Timeout in seconds
            
        Returns:
            CompletedProcess result
        """
        self._logger.debug(f"Running command: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0 and self.verbose:
                self._logger.warning(f"Command failed: {result.stderr}")
            return result
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        except FileNotFoundError:
            raise DependencyError(cmd[0], self._get_install_hint(cmd[0]))
    
    def _ensure_output_dir(self, path: Union[str, Path]) -> Path:
        """Ensure output directory exists."""
        path = Path(path)
        if path.is_file():
            path = path.parent
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def _generate_output_path(
        self,
        input_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        suffix: str = "",
        extension: Optional[str] = None,
    ) -> Path:
        """
        Generate output path based on input path.
        
        Args:
            input_path: Input file path
            output_dir: Output directory (default: same as input)
            suffix: Suffix to add before extension
            extension: New extension (default: keep original)
        """
        input_path = Path(input_path)
        if output_dir:
            output_dir = Path(output_dir)
            self._ensure_output_dir(output_dir)
        else:
            output_dir = input_path.parent
        
        stem = input_path.stem + suffix
        ext = extension if extension else input_path.suffix
        if not ext.startswith("."):
            ext = "." + ext
        
        return output_dir / (stem + ext)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for output naming."""
        return datetime.now().strftime("%Y%m%d-%H%M%S")
    
    def log(self, message: str, level: str = "info") -> None:
        """Log a message."""
        getattr(self._logger, level)(message)
