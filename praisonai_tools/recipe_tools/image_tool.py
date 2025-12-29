"""
Image Tool - Image operations via Pillow and ImageMagick.

Provides:
- Probing image files for metadata
- Optimizing images (compression, format conversion)
- Resizing images
- Creating thumbnails
- Creating montages/contact sheets
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import sys
import os
_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

try:
    from .base import RecipeToolBase
except ImportError:
    from base import RecipeToolBase

logger = logging.getLogger(__name__)

# Try to import Pillow
try:
    from PIL import Image, ImageOps
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    Image = None
    ImageOps = None


@dataclass
class ImageProbeResult:
    """Result of probing an image file."""
    path: str
    format: str
    width: int
    height: int
    mode: str  # RGB, RGBA, L, etc.
    file_size: int
    has_alpha: bool = False
    is_animated: bool = False
    frame_count: int = 1
    dpi: Optional[Tuple[int, int]] = None
    exif: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "format": self.format,
            "width": self.width,
            "height": self.height,
            "mode": self.mode,
            "file_size": self.file_size,
            "has_alpha": self.has_alpha,
            "is_animated": self.is_animated,
            "frame_count": self.frame_count,
            "dpi": self.dpi,
        }


class ImageTool(RecipeToolBase):
    """
    Image operations tool using Pillow and ImageMagick.
    
    Provides image probing, optimization, resizing, and montage creation.
    """
    
    name = "image_tool"
    description = "Image operations via Pillow/ImageMagick"
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check for Pillow and ImageMagick."""
        return {
            "pillow": PILLOW_AVAILABLE,
            "convert": self._check_binary("convert"),
            "montage": self._check_binary("montage"),
            "identify": self._check_binary("identify"),
        }
    
    def _require_pillow(self):
        """Ensure Pillow is available."""
        if not PILLOW_AVAILABLE:
            raise ImportError("Pillow is required. Install with: pip install Pillow")
    
    def probe(self, path: Union[str, Path]) -> ImageProbeResult:
        """
        Probe an image file for metadata.
        
        Args:
            path: Path to image file
            
        Returns:
            ImageProbeResult with file metadata
        """
        self._require_pillow()
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        
        with Image.open(path) as img:
            # Basic info
            width, height = img.size
            format_name = img.format or path.suffix[1:].upper()
            mode = img.mode
            
            # Check for alpha
            has_alpha = mode in ("RGBA", "LA", "PA") or "transparency" in img.info
            
            # Check for animation
            is_animated = getattr(img, "is_animated", False)
            frame_count = getattr(img, "n_frames", 1)
            
            # Get DPI
            dpi = img.info.get("dpi")
            
            # Get EXIF data
            exif = {}
            try:
                exif_data = img._getexif()
                if exif_data:
                    exif = {k: str(v) for k, v in exif_data.items() if isinstance(v, (str, int, float))}
            except (AttributeError, Exception):
                pass
        
        return ImageProbeResult(
            path=str(path),
            format=format_name,
            width=width,
            height=height,
            mode=mode,
            file_size=path.stat().st_size,
            has_alpha=has_alpha,
            is_animated=is_animated,
            frame_count=frame_count,
            dpi=dpi,
            exif=exif,
        )
    
    def optimize(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        quality: int = 85,
        max_size: Optional[Tuple[int, int]] = None,
        format: Optional[str] = None,
    ) -> Path:
        """
        Optimize an image for web/storage.
        
        Args:
            input_path: Input image file
            output_path: Output file (auto-generated if not provided)
            quality: JPEG/WebP quality (1-100)
            max_size: Maximum dimensions (width, height)
            format: Output format (jpg, png, webp)
            
        Returns:
            Path to optimized image
        """
        self._require_pillow()
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Image not found: {input_path}")
        
        # Determine output format
        if format is None:
            format = input_path.suffix[1:].lower()
        format = format.lower()
        if format == "jpeg":
            format = "jpg"
        
        if output_path is None:
            output_path = self._generate_output_path(input_path, suffix="_optimized", extension=format)
        else:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
        
        with Image.open(input_path) as img:
            # Convert mode if needed
            if format in ("jpg", "jpeg") and img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            
            # Resize if max_size specified
            if max_size:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Auto-orient based on EXIF
            img = ImageOps.exif_transpose(img)
            
            # Save with optimization
            save_kwargs = {"optimize": True}
            if format in ("jpg", "jpeg"):
                save_kwargs["quality"] = quality
                save_kwargs["progressive"] = True
            elif format == "webp":
                save_kwargs["quality"] = quality
            elif format == "png":
                save_kwargs["compress_level"] = 9
            
            img.save(output_path, **save_kwargs)
        
        return output_path
    
    def resize(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        scale: Optional[float] = None,
        keep_aspect: bool = True,
    ) -> Path:
        """
        Resize an image.
        
        Args:
            input_path: Input image file
            output_path: Output file (auto-generated if not provided)
            width: Target width
            height: Target height
            scale: Scale factor (e.g., 0.5 for half size)
            keep_aspect: Maintain aspect ratio
            
        Returns:
            Path to resized image
        """
        self._require_pillow()
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Image not found: {input_path}")
        
        if output_path is None:
            suffix = f"_{width}x{height}" if width and height else "_resized"
            output_path = self._generate_output_path(input_path, suffix=suffix)
        else:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
        
        with Image.open(input_path) as img:
            orig_width, orig_height = img.size
            
            # Calculate new dimensions
            if scale:
                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)
            elif width and height:
                if keep_aspect:
                    img.thumbnail((width, height), Image.Resampling.LANCZOS)
                    img.save(output_path)
                    return output_path
                else:
                    new_width, new_height = width, height
            elif width:
                ratio = width / orig_width
                new_width = width
                new_height = int(orig_height * ratio) if keep_aspect else orig_height
            elif height:
                ratio = height / orig_height
                new_height = height
                new_width = int(orig_width * ratio) if keep_aspect else orig_width
            else:
                new_width, new_height = orig_width, orig_height
            
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            resized.save(output_path)
        
        return output_path
    
    def thumbnail(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        size: Tuple[int, int] = (256, 256),
        format: str = "jpg",
        quality: int = 85,
    ) -> Path:
        """
        Create a thumbnail from an image.
        
        Args:
            input_path: Input image file
            output_path: Output file (auto-generated if not provided)
            size: Maximum thumbnail dimensions
            format: Output format
            quality: JPEG quality
            
        Returns:
            Path to thumbnail
        """
        self._require_pillow()
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Image not found: {input_path}")
        
        if output_path is None:
            output_path = self._generate_output_path(input_path, suffix="_thumb", extension=format)
        else:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
        
        with Image.open(input_path) as img:
            # Convert mode if needed
            if format in ("jpg", "jpeg") and img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            
            # Auto-orient
            img = ImageOps.exif_transpose(img)
            
            # Create thumbnail
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Save
            save_kwargs = {}
            if format in ("jpg", "jpeg"):
                save_kwargs["quality"] = quality
            
            img.save(output_path, **save_kwargs)
        
        return output_path
    
    def montage(
        self,
        input_paths: List[Union[str, Path]],
        output_path: Union[str, Path],
        columns: int = 4,
        tile_size: Tuple[int, int] = (200, 200),
        background: str = "white",
        border: int = 2,
    ) -> Path:
        """
        Create a montage/contact sheet from multiple images.
        
        Uses ImageMagick if available, falls back to Pillow.
        
        Args:
            input_paths: List of input image paths
            output_path: Output file path
            columns: Number of columns
            tile_size: Size of each tile
            background: Background color
            border: Border width between tiles
            
        Returns:
            Path to montage image
        """
        output_path = Path(output_path)
        self._ensure_output_dir(output_path.parent)
        
        # Try ImageMagick first (better quality for large montages)
        deps = self.check_dependencies()
        if deps.get("montage"):
            return self._montage_imagemagick(
                input_paths, output_path, columns, tile_size, background, border
            )
        
        # Fall back to Pillow
        self._require_pillow()
        return self._montage_pillow(
            input_paths, output_path, columns, tile_size, background, border
        )
    
    def _montage_imagemagick(
        self,
        input_paths: List[Union[str, Path]],
        output_path: Path,
        columns: int,
        tile_size: Tuple[int, int],
        background: str,
        border: int,
    ) -> Path:
        """Create montage using ImageMagick."""
        cmd = [
            "montage",
            "-geometry", f"{tile_size[0]}x{tile_size[1]}+{border}+{border}",
            "-tile", f"{columns}x",
            "-background", background,
        ]
        
        for p in input_paths:
            cmd.append(str(p))
        
        cmd.append(str(output_path))
        
        result = self._run_command(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"montage failed: {result.stderr}")
        
        return output_path
    
    def _montage_pillow(
        self,
        input_paths: List[Union[str, Path]],
        output_path: Path,
        columns: int,
        tile_size: Tuple[int, int],
        background: str,
        border: int,
    ) -> Path:
        """Create montage using Pillow."""
        n_images = len(input_paths)
        rows = (n_images + columns - 1) // columns
        
        # Calculate canvas size
        canvas_width = columns * (tile_size[0] + border * 2)
        canvas_height = rows * (tile_size[1] + border * 2)
        
        # Create canvas
        canvas = Image.new("RGB", (canvas_width, canvas_height), background)
        
        for i, path in enumerate(input_paths):
            row = i // columns
            col = i % columns
            
            x = col * (tile_size[0] + border * 2) + border
            y = row * (tile_size[1] + border * 2) + border
            
            try:
                with Image.open(path) as img:
                    # Convert to RGB if needed
                    if img.mode in ("RGBA", "LA", "P"):
                        img = img.convert("RGB")
                    
                    # Create thumbnail
                    img.thumbnail(tile_size, Image.Resampling.LANCZOS)
                    
                    # Center in tile
                    offset_x = (tile_size[0] - img.width) // 2
                    offset_y = (tile_size[1] - img.height) // 2
                    
                    canvas.paste(img, (x + offset_x, y + offset_y))
            except Exception as e:
                logger.warning(f"Failed to process {path}: {e}")
        
        canvas.save(output_path)
        return output_path
    
    def batch_resize(
        self,
        input_dir: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        extensions: List[str] = None,
    ) -> List[Path]:
        """
        Batch resize images in a directory.
        
        Args:
            input_dir: Input directory
            output_dir: Output directory
            width: Target width
            height: Target height
            extensions: File extensions to process
            
        Returns:
            List of paths to resized images
        """
        input_dir = Path(input_dir)
        
        if not input_dir.is_dir():
            raise NotADirectoryError(f"Not a directory: {input_dir}")
        
        if output_dir is None:
            output_dir = input_dir / "resized"
        else:
            output_dir = Path(output_dir)
        
        self._ensure_output_dir(output_dir)
        
        if extensions is None:
            extensions = ["jpg", "jpeg", "png", "webp", "gif", "bmp"]
        
        results = []
        for ext in extensions:
            for img_path in input_dir.glob(f"*.{ext}"):
                try:
                    output_path = output_dir / img_path.name
                    self.resize(img_path, output_path, width=width, height=height)
                    results.append(output_path)
                except Exception as e:
                    logger.warning(f"Failed to resize {img_path}: {e}")
        
        return results


# Convenience functions
def image_optimize(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    quality: int = 85,
    max_size: Optional[Tuple[int, int]] = None,
    verbose: bool = False,
) -> Path:
    """Optimize an image."""
    return ImageTool(verbose=verbose).optimize(input_path, output_path, quality, max_size)


def image_resize(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    verbose: bool = False,
) -> Path:
    """Resize an image."""
    return ImageTool(verbose=verbose).resize(input_path, output_path, width, height)


def image_thumbnail(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    size: Tuple[int, int] = (256, 256),
    verbose: bool = False,
) -> Path:
    """Create a thumbnail."""
    return ImageTool(verbose=verbose).thumbnail(input_path, output_path, size)


def image_montage(
    input_paths: List[Union[str, Path]],
    output_path: Union[str, Path],
    columns: int = 4,
    verbose: bool = False,
) -> Path:
    """Create a montage."""
    return ImageTool(verbose=verbose).montage(input_paths, output_path, columns)
