"""
Recipe Tools - Shared tools for Agent-Recipes digital input→output workflows.

This module provides 12 core tools:
1. media_tool - Audio/video operations via ffmpeg
2. doc_tool - PDF/document operations via poppler/pandoc
3. image_tool - Image operations via Pillow/ImageMagick
4. data_tool - CSV/JSON/Parquet operations via pandas
5. repo_tool - Git operations
6. web_tool - URL fetching and content extraction
7. archive_tool - Zip/tar operations
8. whisper_tool - Audio transcription via OpenAI Whisper API
9. llm_tool - Unified LLM interface for all recipes
10. vision_tool - Image analysis, captioning, tagging
11. chart_tool - Chart/visualization generation
12. email_tool - Email parsing and extraction

All tools follow the pattern:
- Structured dataclass return types
- check_dependencies() method
- Safe defaults
- Logging via standard logger
- Clear exceptions with actionable messages
"""

from .base import RecipeToolBase, RecipeToolResult, DependencyError
from .media_tool import MediaTool, MediaProbeResult, media_probe, media_extract_audio, media_normalize, media_trim, media_extract_frames
from .doc_tool import DocTool, DocProbeResult, doc_to_markdown, doc_to_pdf, doc_extract_text, doc_extract_images
from .image_tool import ImageTool, ImageProbeResult, image_optimize, image_resize, image_thumbnail, image_montage
from .data_tool import DataTool, DataProfileResult, data_profile, data_clean, data_convert, data_infer_schema
from .repo_tool import RepoTool, RepoInfo, repo_log, repo_diff, repo_files, repo_info
from .web_tool import WebTool, WebContent, web_fetch, web_extract_article, web_fetch_sitemap
from .archive_tool import ArchiveTool, ArchiveManifest, archive_create, archive_extract, archive_list
from .whisper_tool import WhisperTool, TranscriptResult, whisper_transcribe
from .llm_tool import LLMTool, LLMResponse, LLMMessage, llm_complete, llm_extract_json
from .vision_tool import VisionTool, VisionResult, vision_caption, vision_tag, vision_ocr
from .chart_tool import ChartTool, ChartResult, chart_bar, chart_line, chart_pie
from .email_tool import EmailTool, ParsedEmail, EmailAttachment, ExtractedData, email_parse, email_extract

__all__ = [
    # Base
    "RecipeToolBase",
    "RecipeToolResult",
    "DependencyError",
    # Media
    "MediaTool",
    "MediaProbeResult",
    "media_probe",
    "media_extract_audio",
    "media_normalize",
    "media_trim",
    "media_extract_frames",
    # Doc
    "DocTool",
    "DocProbeResult",
    "doc_to_markdown",
    "doc_to_pdf",
    "doc_extract_text",
    "doc_extract_images",
    # Image
    "ImageTool",
    "ImageProbeResult",
    "image_optimize",
    "image_resize",
    "image_thumbnail",
    "image_montage",
    # Data
    "DataTool",
    "DataProfileResult",
    "data_profile",
    "data_clean",
    "data_convert",
    "data_infer_schema",
    # Repo
    "RepoTool",
    "RepoInfo",
    "repo_log",
    "repo_diff",
    "repo_files",
    "repo_info",
    # Web
    "WebTool",
    "WebContent",
    "web_fetch",
    "web_extract_article",
    "web_fetch_sitemap",
    # Archive
    "ArchiveTool",
    "ArchiveManifest",
    "archive_create",
    "archive_extract",
    "archive_list",
    # Whisper
    "WhisperTool",
    "TranscriptResult",
    "whisper_transcribe",
    # LLM
    "LLMTool",
    "LLMResponse",
    "LLMMessage",
    "llm_complete",
    "llm_extract_json",
    # Vision
    "VisionTool",
    "VisionResult",
    "vision_caption",
    "vision_tag",
    "vision_ocr",
    # Chart
    "ChartTool",
    "ChartResult",
    "chart_bar",
    "chart_line",
    "chart_pie",
    # Email
    "EmailTool",
    "ParsedEmail",
    "EmailAttachment",
    "ExtractedData",
    "email_parse",
    "email_extract",
]
