"""
Archive Tool - Zip/tar operations.

Provides:
- Creating archives (zip, tar, tar.gz)
- Extracting archives
- Listing archive contents
- Generating manifests with checksums
"""

import hashlib
import logging
import os
import tarfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

import sys
import os as _os
_dir = _os.path.dirname(_os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

try:
    from .base import RecipeToolBase
except ImportError:
    from base import RecipeToolBase

logger = logging.getLogger(__name__)


@dataclass
class ArchiveEntry:
    """Entry in an archive."""
    name: str
    size: int
    is_dir: bool
    sha256: Optional[str] = None


@dataclass
class ArchiveManifest:
    """Manifest of an archive."""
    path: str
    format: str
    total_size: int
    file_count: int
    entries: List[ArchiveEntry] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "format": self.format,
            "total_size": self.total_size,
            "file_count": self.file_count,
            "entries": [
                {"name": e.name, "size": e.size, "is_dir": e.is_dir, "sha256": e.sha256}
                for e in self.entries
            ],
        }


class ArchiveTool(RecipeToolBase):
    """
    Archive operations tool using stdlib.
    
    Provides archive creation, extraction, and listing.
    """
    
    name = "archive_tool"
    description = "Zip/tar archive operations"
    
    # Default exclusions
    DEFAULT_EXCLUDES = [
        ".git",
        ".svn",
        ".hg",
        "__pycache__",
        "*.pyc",
        ".DS_Store",
        "Thumbs.db",
        "node_modules",
        ".venv",
        "venv",
        ".env",
        "*.egg-info",
    ]
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check for archive support (stdlib, always available)."""
        return {
            "zipfile": True,
            "tarfile": True,
        }
    
    def _should_exclude(self, path: Path, excludes: List[str]) -> bool:
        """Check if path should be excluded."""
        import fnmatch
        
        name = path.name
        for pattern in excludes:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False
    
    def _calculate_sha256(self, path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def create(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        format: str = "zip",
        excludes: Optional[List[str]] = None,
        include_checksums: bool = True,
        compression_level: int = 6,
    ) -> Path:
        """
        Create an archive from a file or directory.
        
        Args:
            input_path: Input file or directory
            output_path: Output archive path
            format: Archive format (zip, tar, tar.gz, tar.bz2)
            excludes: Patterns to exclude
            include_checksums: Calculate SHA256 for files
            compression_level: Compression level (0-9)
            
        Returns:
            Path to created archive
        """
        input_path = Path(input_path).resolve()
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input not found: {input_path}")
        
        if excludes is None:
            excludes = self.DEFAULT_EXCLUDES
        
        # Determine output path
        if output_path is None:
            ext = {"zip": ".zip", "tar": ".tar", "tar.gz": ".tar.gz", "tar.bz2": ".tar.bz2"}
            output_path = input_path.parent / f"{input_path.name}{ext.get(format, '.zip')}"
        else:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
        
        if format == "zip":
            return self._create_zip(input_path, output_path, excludes, compression_level)
        elif format in ("tar", "tar.gz", "tar.bz2"):
            return self._create_tar(input_path, output_path, format, excludes)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _create_zip(
        self,
        input_path: Path,
        output_path: Path,
        excludes: List[str],
        compression_level: int,
    ) -> Path:
        """Create a zip archive."""
        compression = zipfile.ZIP_DEFLATED
        
        with zipfile.ZipFile(output_path, "w", compression, compresslevel=compression_level) as zf:
            if input_path.is_file():
                zf.write(input_path, input_path.name)
            else:
                for root, dirs, files in os.walk(input_path):
                    # Filter directories in-place
                    dirs[:] = [d for d in dirs if not self._should_exclude(Path(d), excludes)]
                    
                    for file in files:
                        file_path = Path(root) / file
                        if not self._should_exclude(file_path, excludes):
                            arcname = file_path.relative_to(input_path)
                            zf.write(file_path, arcname)
        
        return output_path
    
    def _create_tar(
        self,
        input_path: Path,
        output_path: Path,
        format: str,
        excludes: List[str],
    ) -> Path:
        """Create a tar archive."""
        mode = {"tar": "w", "tar.gz": "w:gz", "tar.bz2": "w:bz2"}[format]
        
        def filter_func(tarinfo):
            if self._should_exclude(Path(tarinfo.name), excludes):
                return None
            return tarinfo
        
        with tarfile.open(output_path, mode) as tf:
            tf.add(input_path, arcname=input_path.name, filter=filter_func)
        
        return output_path
    
    def extract(
        self,
        input_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Path:
        """
        Extract an archive.
        
        Args:
            input_path: Archive file
            output_dir: Output directory
            
        Returns:
            Path to extraction directory
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Archive not found: {input_path}")
        
        if output_dir is None:
            output_dir = input_path.parent / input_path.stem
        else:
            output_dir = Path(output_dir)
        
        self._ensure_output_dir(output_dir)
        
        # Detect format
        if input_path.suffix == ".zip":
            with zipfile.ZipFile(input_path, "r") as zf:
                zf.extractall(output_dir)
        elif input_path.suffix in (".tar", ".gz", ".bz2", ".xz"):
            with tarfile.open(input_path, "r:*") as tf:
                tf.extractall(output_dir)
        else:
            raise ValueError(f"Unknown archive format: {input_path.suffix}")
        
        return output_dir
    
    def list(
        self,
        path: Union[str, Path],
        include_checksums: bool = False,
    ) -> ArchiveManifest:
        """
        List contents of an archive.
        
        Args:
            path: Archive file
            include_checksums: Calculate checksums (slower)
            
        Returns:
            ArchiveManifest with entries
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Archive not found: {path}")
        
        entries = []
        total_size = 0
        
        if path.suffix == ".zip":
            format_name = "zip"
            with zipfile.ZipFile(path, "r") as zf:
                for info in zf.infolist():
                    entries.append(ArchiveEntry(
                        name=info.filename,
                        size=info.file_size,
                        is_dir=info.is_dir(),
                    ))
                    total_size += info.file_size
        else:
            format_name = "tar"
            with tarfile.open(path, "r:*") as tf:
                for info in tf.getmembers():
                    entries.append(ArchiveEntry(
                        name=info.name,
                        size=info.size,
                        is_dir=info.isdir(),
                    ))
                    total_size += info.size
        
        return ArchiveManifest(
            path=str(path),
            format=format_name,
            total_size=total_size,
            file_count=len([e for e in entries if not e.is_dir]),
            entries=entries,
        )
    
    def create_manifest(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        excludes: Optional[List[str]] = None,
    ) -> Dict:
        """
        Create a manifest file for a directory.
        
        Args:
            input_path: Directory to manifest
            output_path: Output JSON file
            excludes: Patterns to exclude
            
        Returns:
            Manifest dictionary
        """
        input_path = Path(input_path).resolve()
        
        if not input_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {input_path}")
        
        if excludes is None:
            excludes = self.DEFAULT_EXCLUDES
        
        entries = []
        total_size = 0
        
        for root, dirs, files in os.walk(input_path):
            # Filter directories
            dirs[:] = [d for d in dirs if not self._should_exclude(Path(d), excludes)]
            
            for file in files:
                file_path = Path(root) / file
                if not self._should_exclude(file_path, excludes):
                    rel_path = file_path.relative_to(input_path)
                    size = file_path.stat().st_size
                    sha256 = self._calculate_sha256(file_path)
                    
                    entries.append({
                        "path": str(rel_path),
                        "size": size,
                        "sha256": sha256,
                    })
                    total_size += size
        
        manifest = {
            "source": str(input_path),
            "created_at": self._get_timestamp(),
            "total_size": total_size,
            "file_count": len(entries),
            "files": entries,
        }
        
        if output_path:
            import json
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
            output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        
        return manifest
    
    def create_checksums(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        algorithm: str = "sha256",
    ) -> str:
        """
        Create checksums file for a directory.
        
        Args:
            input_path: Directory
            output_path: Output checksums file
            algorithm: Hash algorithm (sha256, md5)
            
        Returns:
            Checksums content
        """
        input_path = Path(input_path).resolve()
        
        if not input_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {input_path}")
        
        lines = []
        
        for root, dirs, files in os.walk(input_path):
            dirs[:] = [d for d in dirs if not self._should_exclude(Path(d), self.DEFAULT_EXCLUDES)]
            
            for file in sorted(files):
                file_path = Path(root) / file
                if not self._should_exclude(file_path, self.DEFAULT_EXCLUDES):
                    rel_path = file_path.relative_to(input_path)
                    
                    if algorithm == "sha256":
                        checksum = self._calculate_sha256(file_path)
                    elif algorithm == "md5":
                        md5 = hashlib.md5()
                        with open(file_path, "rb") as f:
                            for chunk in iter(lambda: f.read(8192), b""):
                                md5.update(chunk)
                        checksum = md5.hexdigest()
                    else:
                        raise ValueError(f"Unknown algorithm: {algorithm}")
                    
                    lines.append(f"{checksum}  {rel_path}")
        
        content = "\n".join(lines)
        
        if output_path:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
            output_path.write_text(content, encoding="utf-8")
        
        return content


# Convenience functions
def archive_create(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    format: str = "zip",
    verbose: bool = False,
) -> Path:
    """Create an archive."""
    return ArchiveTool(verbose=verbose).create(input_path, output_path, format)


def archive_extract(
    input_path: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    verbose: bool = False,
) -> Path:
    """Extract an archive."""
    return ArchiveTool(verbose=verbose).extract(input_path, output_dir)


def archive_list(
    path: Union[str, Path],
    verbose: bool = False,
) -> ArchiveManifest:
    """List archive contents."""
    return ArchiveTool(verbose=verbose).list(path)
