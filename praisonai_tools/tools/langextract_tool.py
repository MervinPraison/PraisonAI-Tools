"""Langextract Tool for PraisonAI Agents.

Interactive text visualization and annotation with highlighted extractions.

Usage:
    from praisonai_tools import langextract_extract, langextract_render_file
    
    # Extract from text
    result = langextract_extract(
        text="John Doe works at OpenAI",
        extractions=["John Doe", "OpenAI"],
        document_id="contract-analysis"
    )
    
    # Extract from file
    result = langextract_render_file(
        file_path="/path/to/document.txt",
        extractions=["important terms"],
        auto_open=True
    )

Installation:
    pip install praisonai-tools[langextract]
    # or
    pip install praisonai-tools langextract
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool
from praisonai_tools.tools.decorator import tool

logger = logging.getLogger(__name__)


def _get_langextract():
    """Lazy import of langextract with helpful error message."""
    try:
        import langextract as lx
        return lx
    except ImportError:
        return None


def _create_annotated_document(text: str, extractions: List[str], document_id: str):
    """Create langextract AnnotatedDocument with extractions as Extraction objects."""
    lx = _get_langextract()
    if not lx:
        return None

    # Find all extraction positions and wrap as Extraction objects
    extraction_objects = []
    for i, extraction_text in enumerate(extractions or []):
        if not extraction_text.strip():
            continue
        start_pos = 0
        while True:
            pos = text.lower().find(extraction_text.lower(), start_pos)
            if pos == -1:
                break
            extraction_objects.append(lx.data.Extraction(
                extraction_class=f"extraction_{i}",
                extraction_text=extraction_text,
                char_interval=lx.data.CharInterval(
                    start_pos=pos,
                    end_pos=pos + len(extraction_text),
                ),
                attributes={
                    "index": i,
                    "original_text": extraction_text,
                    "tool": "langextract_extract",
                },
            ))
            start_pos = pos + 1

    return lx.data.AnnotatedDocument(
        document_id=document_id,
        text=text,
        extractions=extraction_objects,
    )


class LangExtractTool(BaseTool):
    """Tool for interactive text visualization with langextract."""
    
    name = "langextract"
    description = "Create interactive HTML visualizations from text with highlighted extractions."
    
    def run(
        self,
        action: str = "extract",
        text: Optional[str] = None,
        file_path: Optional[str] = None,
        extractions: Optional[List[str]] = None,
        document_id: str = "agent-analysis",
        output_path: Optional[str] = None,
        auto_open: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Run langextract action."""
        if action == "extract":
            return self.extract(
                text=text,
                extractions=extractions,
                document_id=document_id,
                output_path=output_path,
                auto_open=auto_open
            )
        elif action == "render_file":
            return self.render_file(
                file_path=file_path,
                extractions=extractions,
                output_path=output_path,
                auto_open=auto_open
            )
        return {"error": f"Unknown action: {action}"}
    
    def extract(
        self,
        text: str,
        extractions: Optional[List[str]] = None,
        document_id: str = "agent-analysis",
        output_path: Optional[str] = None,
        auto_open: bool = False
    ) -> Dict[str, Any]:
        """Extract and annotate text using langextract for interactive visualization."""
        if not text:
            return {"error": "text parameter is required"}
        
        lx = _get_langextract()
        if not lx:
            return {
                "error": "langextract not installed. Install with: pip install langextract"
            }
        
        try:
            # Use provided extractions or empty list
            extractions = extractions or []
            
            # Create annotated document
            doc = _create_annotated_document(text, extractions, document_id)
            if not doc:
                return {"error": "Failed to create annotated document"}
            
            # Determine output path
            if not output_path:
                output_path = f"{document_id}.html"
            
            output_path = Path(output_path).resolve()
            
            # Save annotated documents and visualize
            lx.io.save_annotated_documents([doc], str(output_path.parent / f"{document_id}.jsonl"))
            lx.visualize(str(output_path))
            
            result = {
                "success": True,
                "document_id": document_id,
                "output_path": str(output_path),
                "extractions_count": len(extractions),
                "text_length": len(text)
            }
            
            # Auto-open in browser if requested
            if auto_open:
                try:
                    import webbrowser
                    file_uri = output_path.as_uri()
                    webbrowser.open(file_uri)
                    result["auto_opened"] = file_uri
                except Exception as e:
                    result["auto_open_error"] = str(e)
            
            return result
            
        except Exception as e:
            logger.error(f"Langextract extract error: {e}")
            return {"error": str(e)}
    
    def render_file(
        self,
        file_path: str,
        extractions: Optional[List[str]] = None,
        output_path: Optional[str] = None,
        auto_open: bool = False
    ) -> Dict[str, Any]:
        """Read a text file and create langextract visualization."""
        if not file_path:
            return {"error": "file_path parameter is required"}
        
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {"error": f"File not found: {file_path}"}
            
            # Read file content
            try:
                text = file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Try with different encoding
                text = file_path.read_text(encoding='latin1')
            
            # Generate document ID from filename
            document_id = file_path.stem
            
            # Use extract method with file content
            return self.extract(
                text=text,
                extractions=extractions,
                document_id=document_id,
                output_path=output_path,
                auto_open=auto_open
            )
            
        except Exception as e:
            logger.error(f"Langextract render_file error: {e}")
            return {"error": str(e)}


@tool
def langextract_extract(
    text: str,
    extractions: Optional[List[str]] = None,
    document_id: str = "agent-analysis",
    output_path: Optional[str] = None,
    auto_open: bool = False
) -> Dict[str, Any]:
    """Extract and annotate text using langextract for interactive visualization.
    
    Creates an interactive HTML document with highlighted extractions that can be
    viewed in a browser. Useful for text analysis, entity extraction, and 
    document annotation workflows.
    
    Args:
        text: The text content to analyze and annotate
        extractions: List of text spans to highlight (optional)
        document_id: Unique identifier for the document (default: "agent-analysis")
        output_path: Where to save the HTML file (optional, auto-generated if not provided)
        auto_open: Whether to automatically open the result in a browser (default: False)
    
    Returns:
        Dictionary with success status, file paths, and extraction statistics
    """
    return LangExtractTool().extract(
        text=text,
        extractions=extractions,
        document_id=document_id,
        output_path=output_path,
        auto_open=auto_open
    )


@tool
def langextract_render_file(
    file_path: str,
    extractions: Optional[List[str]] = None,
    output_path: Optional[str] = None,
    auto_open: bool = False
) -> Dict[str, Any]:
    """Read a text file and create langextract visualization.
    
    WARNING: This tool can read arbitrary files from the filesystem.
    Use with caution and ensure file_path is trusted.
    
    Args:
        file_path: Path to the text file to analyze
        extractions: List of text spans to highlight (optional)
        output_path: Where to save the HTML file (optional, auto-generated if not provided)
        auto_open: Whether to automatically open the result in a browser (default: False)
    
    Returns:
        Dictionary with success status, file paths, and extraction statistics
    """
    return LangExtractTool().render_file(
        file_path=file_path,
        extractions=extractions,
        output_path=output_path,
        auto_open=auto_open
    )