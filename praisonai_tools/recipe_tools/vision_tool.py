"""
Vision Tool - Image analysis, captioning, and tagging with LLM vision models.

Provides capabilities for:
- Image captioning and alt-text generation
- Object detection and tagging
- OCR and text extraction from images
- Image-based Q&A
"""

import os
import base64
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    from .base import RecipeToolBase, RecipeToolResult
except ImportError:
    from base import RecipeToolBase, RecipeToolResult

logger = logging.getLogger(__name__)


@dataclass
class VisionResult(RecipeToolResult):
    """Result from vision analysis."""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    objects: List[Dict[str, Any]] = field(default_factory=list)
    text_content: str = ""
    confidence: float = 0.0
    model: str = ""
    provider: str = ""


class VisionTool(RecipeToolBase):
    """Vision analysis tool using LLM vision models."""
    
    SUPPORTED_PROVIDERS = ["openai", "anthropic", "google"]
    SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]
    
    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        redact_pii: bool = True,
    ):
        self.provider = provider.lower()
        self.model = model or self._default_model()
        self.api_key = api_key or self._get_api_key()
        self.redact_pii = redact_pii
        self._client = None
    
    def _default_model(self) -> str:
        """Get default vision model for provider."""
        defaults = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-haiku-20240307",
            "google": "gemini-1.5-flash",
        }
        return defaults.get(self.provider, "gpt-4o-mini")
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment."""
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        env_var = env_vars.get(self.provider)
        return os.environ.get(env_var) if env_var else None
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are available."""
        deps = {}
        
        if self.provider == "openai":
            try:
                import openai
                deps["openai"] = True
            except ImportError:
                deps["openai"] = False
        elif self.provider == "anthropic":
            try:
                import anthropic
                deps["anthropic"] = True
            except ImportError:
                deps["anthropic"] = False
        elif self.provider == "google":
            try:
                import google.generativeai
                deps["google-generativeai"] = True
            except ImportError:
                deps["google-generativeai"] = False
        
        deps["api_key"] = bool(self.api_key)
        return deps
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def _get_mime_type(self, image_path: str) -> str:
        """Get MIME type from file extension."""
        ext = Path(image_path).suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        return mime_types.get(ext, "image/jpeg")
    
    def _get_client(self):
        """Get or create the API client."""
        if self._client is not None:
            return self._client
        
        if self.provider == "openai":
            import openai
            self._client = openai.OpenAI(api_key=self.api_key)
        elif self.provider == "anthropic":
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        elif self.provider == "google":
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model)
        
        return self._client
    
    def analyze(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        include_tags: bool = True,
        include_objects: bool = False,
        include_text: bool = False,
    ) -> VisionResult:
        """
        Analyze an image with vision model.
        
        Args:
            image_path: Path to image file
            prompt: Custom prompt for analysis
            include_tags: Include keyword tags
            include_objects: Include object detection
            include_text: Include OCR text extraction
            
        Returns:
            VisionResult with analysis
        """
        if not os.path.exists(image_path):
            return VisionResult(success=False, error=f"Image not found: {image_path}")
        
        ext = Path(image_path).suffix.lower()
        if ext not in self.SUPPORTED_FORMATS:
            return VisionResult(success=False, error=f"Unsupported format: {ext}")
        
        # Build analysis prompt
        if prompt:
            analysis_prompt = prompt
        else:
            parts = ["Describe this image in detail."]
            if include_tags:
                parts.append("List relevant tags/keywords.")
            if include_objects:
                parts.append("Identify and list all objects visible.")
            if include_text:
                parts.append("Extract any text visible in the image.")
            analysis_prompt = " ".join(parts)
        
        if self.redact_pii:
            analysis_prompt += " Do not include any personally identifiable information (names, addresses, phone numbers, etc.) in your response."
        
        client = self._get_client()
        
        if self.provider == "openai":
            return self._analyze_openai(client, image_path, analysis_prompt, include_tags, include_text)
        elif self.provider == "anthropic":
            return self._analyze_anthropic(client, image_path, analysis_prompt, include_tags, include_text)
        elif self.provider == "google":
            return self._analyze_google(client, image_path, analysis_prompt, include_tags, include_text)
        else:
            return VisionResult(success=False, error=f"Unsupported provider: {self.provider}")
    
    def _analyze_openai(
        self,
        client,
        image_path: str,
        prompt: str,
        include_tags: bool,
        include_text: bool,
    ) -> VisionResult:
        """Analyze using OpenAI Vision."""
        base64_image = self._encode_image(image_path)
        mime_type = self._get_mime_type(image_path)
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
        )
        
        content = response.choices[0].message.content
        
        # Parse tags if requested
        tags = []
        if include_tags and "tags" in prompt.lower():
            import re
            tag_match = re.search(r'tags?[:\s]+([^\n]+)', content, re.IGNORECASE)
            if tag_match:
                tags = [t.strip() for t in tag_match.group(1).split(',')]
        
        return VisionResult(
            success=True,
            description=content,
            tags=tags,
            model=self.model,
            provider=self.provider,
        )
    
    def _analyze_anthropic(
        self,
        client,
        image_path: str,
        prompt: str,
        include_tags: bool,
        include_text: bool,
    ) -> VisionResult:
        """Analyze using Anthropic Vision."""
        base64_image = self._encode_image(image_path)
        mime_type = self._get_mime_type(image_path)
        
        response = client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": base64_image,
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        )
        
        content = response.content[0].text
        
        return VisionResult(
            success=True,
            description=content,
            model=self.model,
            provider=self.provider,
        )
    
    def _analyze_google(
        self,
        client,
        image_path: str,
        prompt: str,
        include_tags: bool,
        include_text: bool,
    ) -> VisionResult:
        """Analyze using Google Vision."""
        import PIL.Image
        
        image = PIL.Image.open(image_path)
        response = client.generate_content([prompt, image])
        
        return VisionResult(
            success=True,
            description=response.text,
            model=self.model,
            provider=self.provider,
        )
    
    def caption(self, image_path: str, style: str = "descriptive") -> str:
        """
        Generate a caption for an image.
        
        Args:
            image_path: Path to image
            style: Caption style - descriptive, concise, alt-text, social
            
        Returns:
            Caption string
        """
        prompts = {
            "descriptive": "Describe this image in 2-3 sentences.",
            "concise": "Describe this image in one sentence.",
            "alt-text": "Write an accessibility alt-text description for this image. Be concise but descriptive.",
            "social": "Write an engaging social media caption for this image.",
        }
        
        prompt = prompts.get(style, prompts["descriptive"])
        result = self.analyze(image_path, prompt=prompt, include_tags=False)
        return result.description if result.success else ""
    
    def tag(self, image_path: str, max_tags: int = 10) -> List[str]:
        """
        Generate tags/keywords for an image.
        
        Args:
            image_path: Path to image
            max_tags: Maximum number of tags
            
        Returns:
            List of tags
        """
        prompt = f"List up to {max_tags} relevant tags/keywords for this image, separated by commas. Output only the tags, nothing else."
        result = self.analyze(image_path, prompt=prompt, include_tags=True)
        
        if result.success:
            # Parse comma-separated tags from response
            tags = [t.strip() for t in result.description.split(',')]
            return tags[:max_tags]
        return []
    
    def extract_text(self, image_path: str) -> str:
        """
        Extract text from an image (OCR).
        
        Args:
            image_path: Path to image
            
        Returns:
            Extracted text
        """
        prompt = "Extract and transcribe all text visible in this image. Output only the extracted text, preserving the layout as much as possible."
        result = self.analyze(image_path, prompt=prompt, include_text=True)
        return result.description if result.success else ""
    
    def ask(self, image_path: str, question: str) -> str:
        """
        Ask a question about an image.
        
        Args:
            image_path: Path to image
            question: Question to ask
            
        Returns:
            Answer string
        """
        result = self.analyze(image_path, prompt=question)
        return result.description if result.success else ""


# Convenience functions
def vision_caption(image_path: str, style: str = "descriptive", provider: str = "openai") -> str:
    """Generate caption for image."""
    tool = VisionTool(provider=provider)
    return tool.caption(image_path, style)


def vision_tag(image_path: str, max_tags: int = 10, provider: str = "openai") -> List[str]:
    """Generate tags for image."""
    tool = VisionTool(provider=provider)
    return tool.tag(image_path, max_tags)


def vision_ocr(image_path: str, provider: str = "openai") -> str:
    """Extract text from image."""
    tool = VisionTool(provider=provider)
    return tool.extract_text(image_path)


__all__ = [
    "VisionTool",
    "VisionResult",
    "vision_caption",
    "vision_tag",
    "vision_ocr",
]
