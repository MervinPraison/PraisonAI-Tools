"""
Doc Tool - PDF/document operations via poppler/pandoc.

Provides:
- Probing PDF files for metadata
- Converting PDF to markdown
- Converting markdown to PDF
- Extracting text from PDFs
- Extracting images from PDFs
- OCR support (optional, via tesseract)
"""

import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

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


@dataclass
class DocProbeResult:
    """Result of probing a document file."""
    path: str
    format: str  # pdf, docx, etc.
    pages: int
    title: Optional[str] = None
    author: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    encrypted: bool = False
    file_size: int = 0
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "format": self.format,
            "pages": self.pages,
            "title": self.title,
            "author": self.author,
            "creator": self.creator,
            "producer": self.producer,
            "creation_date": self.creation_date,
            "modification_date": self.modification_date,
            "encrypted": self.encrypted,
            "file_size": self.file_size,
        }


class DocTool(RecipeToolBase):
    """
    Document operations tool using poppler and pandoc.
    
    Provides PDF probing, text/image extraction, and format conversion.
    """
    
    name = "doc_tool"
    description = "PDF/document operations via poppler/pandoc"
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check for poppler and pandoc utilities."""
        return {
            "pdftotext": self._check_binary("pdftotext"),
            "pdfinfo": self._check_binary("pdfinfo"),
            "pdfimages": self._check_binary("pdfimages"),
            "pandoc": self._check_binary("pandoc"),
            "tesseract": self._check_binary("tesseract"),
        }
    
    def probe(self, path: Union[str, Path]) -> DocProbeResult:
        """
        Probe a PDF file for metadata.
        
        Args:
            path: Path to PDF file
            
        Returns:
            DocProbeResult with file metadata
        """
        self.require_dependencies(["pdfinfo"])
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {path}")
        
        cmd = ["pdfinfo", str(path)]
        result = self._run_command(cmd)
        
        if result.returncode != 0:
            raise RuntimeError(f"pdfinfo failed: {result.stderr}")
        
        # Parse pdfinfo output
        metadata = {}
        for line in result.stdout.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip().lower().replace(" ", "_")] = value.strip()
        
        # Extract specific fields
        pages = int(metadata.get("pages", 0))
        encrypted = metadata.get("encrypted", "no").lower() == "yes"
        
        return DocProbeResult(
            path=str(path),
            format="pdf",
            pages=pages,
            title=metadata.get("title"),
            author=metadata.get("author"),
            creator=metadata.get("creator"),
            producer=metadata.get("producer"),
            creation_date=metadata.get("creationdate"),
            modification_date=metadata.get("moddate"),
            encrypted=encrypted,
            file_size=path.stat().st_size,
            metadata=metadata,
        )
    
    def extract_text(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        layout: bool = False,
        first_page: Optional[int] = None,
        last_page: Optional[int] = None,
    ) -> str:
        """
        Extract text from PDF file.
        
        Args:
            input_path: Input PDF file
            output_path: Output text file (optional)
            layout: Preserve layout (default: False)
            first_page: First page to extract (1-indexed)
            last_page: Last page to extract
            
        Returns:
            Extracted text content
        """
        self.require_dependencies(["pdftotext"])
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"PDF not found: {input_path}")
        
        cmd = ["pdftotext"]
        
        if layout:
            cmd.append("-layout")
        
        if first_page is not None:
            cmd.extend(["-f", str(first_page)])
        
        if last_page is not None:
            cmd.extend(["-l", str(last_page)])
        
        cmd.extend([str(input_path), "-"])  # Output to stdout
        
        result = self._run_command(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"pdftotext failed: {result.stderr}")
        
        text = result.stdout
        
        if output_path:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
            output_path.write_text(text, encoding="utf-8")
        
        return text
    
    def extract_images(
        self,
        input_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        format: str = "png",
        first_page: Optional[int] = None,
        last_page: Optional[int] = None,
    ) -> List[Path]:
        """
        Extract images from PDF file.
        
        Args:
            input_path: Input PDF file
            output_dir: Output directory for images
            format: Output format (png, jpg, ppm)
            first_page: First page to extract from
            last_page: Last page to extract from
            
        Returns:
            List of paths to extracted images
        """
        self.require_dependencies(["pdfimages"])
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"PDF not found: {input_path}")
        
        if output_dir is None:
            output_dir = input_path.parent / f"{input_path.stem}_images"
        else:
            output_dir = Path(output_dir)
        
        self._ensure_output_dir(output_dir)
        
        prefix = str(output_dir / "image")
        
        cmd = ["pdfimages"]
        
        # Format flag
        if format.lower() == "png":
            cmd.append("-png")
        elif format.lower() in ("jpg", "jpeg"):
            cmd.append("-j")
        # Default is ppm
        
        if first_page is not None:
            cmd.extend(["-f", str(first_page)])
        
        if last_page is not None:
            cmd.extend(["-l", str(last_page)])
        
        cmd.extend([str(input_path), prefix])
        
        result = self._run_command(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"pdfimages failed: {result.stderr}")
        
        # Collect extracted images
        images = []
        for ext in ["png", "jpg", "ppm", "pbm", "pgm"]:
            images.extend(output_dir.glob(f"image-*.{ext}"))
        
        return sorted(images)
    
    def to_markdown(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        extract_images: bool = True,
        use_ocr: bool = False,
    ) -> str:
        """
        Convert PDF to Markdown.
        
        Args:
            input_path: Input PDF file
            output_path: Output markdown file (optional)
            extract_images: Also extract images
            use_ocr: Use OCR for scanned documents
            
        Returns:
            Markdown content
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"PDF not found: {input_path}")
        
        # Determine output directory for images
        if output_path:
            output_path = Path(output_path)
            images_dir = output_path.parent / "images"
        else:
            images_dir = input_path.parent / f"{input_path.stem}_images"
        
        # Extract text
        if use_ocr:
            text = self._ocr_pdf(input_path)
        else:
            text = self.extract_text(input_path)
        
        # Convert text to markdown (basic formatting)
        markdown = self._text_to_markdown(text)
        
        # Extract images if requested
        image_refs = []
        if extract_images:
            try:
                images = self.extract_images(input_path, images_dir)
                for i, img in enumerate(images):
                    rel_path = f"images/{img.name}"
                    image_refs.append(f"\n![Image {i+1}]({rel_path})\n")
            except Exception as e:
                logger.warning(f"Image extraction failed: {e}")
        
        # Append image references
        if image_refs:
            markdown += "\n\n## Extracted Images\n"
            markdown += "\n".join(image_refs)
        
        if output_path:
            self._ensure_output_dir(output_path.parent)
            output_path.write_text(markdown, encoding="utf-8")
        
        return markdown
    
    def to_pdf(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        template: Optional[str] = None,
    ) -> Path:
        """
        Convert Markdown to PDF using pandoc.
        
        Args:
            input_path: Input markdown file
            output_path: Output PDF file
            template: LaTeX template (optional)
            
        Returns:
            Path to created PDF
        """
        self.require_dependencies(["pandoc"])
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {input_path}")
        
        if output_path is None:
            output_path = self._generate_output_path(input_path, extension="pdf")
        else:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
        
        cmd = [
            "pandoc",
            str(input_path),
            "-o", str(output_path),
            "--pdf-engine=pdflatex",
        ]
        
        if template:
            cmd.extend(["--template", template])
        
        result = self._run_command(cmd)
        if result.returncode != 0:
            # Try with xelatex if pdflatex fails
            cmd[-1] = "--pdf-engine=xelatex"
            result = self._run_command(cmd)
            if result.returncode != 0:
                raise RuntimeError(f"pandoc failed: {result.stderr}")
        
        return output_path
    
    def _ocr_pdf(self, path: Path) -> str:
        """OCR a PDF using tesseract."""
        self.require_dependencies(["tesseract", "pdfimages"])
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Extract images from PDF
            images = self.extract_images(path, tmpdir, format="png")
            
            if not images:
                return ""
            
            # OCR each image
            texts = []
            for img in images:
                cmd = ["tesseract", str(img), "stdout"]
                result = self._run_command(cmd)
                if result.returncode == 0:
                    texts.append(result.stdout)
            
            return "\n\n".join(texts)
    
    def _text_to_markdown(self, text: str) -> str:
        """Convert plain text to basic markdown."""
        lines = text.split("\n")
        markdown_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                markdown_lines.append("")
                continue
            
            # Detect potential headings (all caps, short lines)
            if stripped.isupper() and len(stripped) < 80:
                markdown_lines.append(f"## {stripped.title()}")
            else:
                markdown_lines.append(stripped)
        
        return "\n".join(markdown_lines)


# Convenience functions
def doc_to_markdown(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    extract_images: bool = True,
    use_ocr: bool = False,
    verbose: bool = False,
) -> str:
    """Convert PDF to Markdown."""
    return DocTool(verbose=verbose).to_markdown(input_path, output_path, extract_images, use_ocr)


def doc_to_pdf(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    verbose: bool = False,
) -> Path:
    """Convert Markdown to PDF."""
    return DocTool(verbose=verbose).to_pdf(input_path, output_path)


def doc_extract_text(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    layout: bool = False,
    verbose: bool = False,
) -> str:
    """Extract text from PDF."""
    return DocTool(verbose=verbose).extract_text(input_path, output_path, layout)


def doc_extract_images(
    input_path: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    format: str = "png",
    verbose: bool = False,
) -> List[Path]:
    """Extract images from PDF."""
    return DocTool(verbose=verbose).extract_images(input_path, output_dir, format)
