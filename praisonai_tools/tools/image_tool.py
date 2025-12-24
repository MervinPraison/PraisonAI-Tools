"""Image Generation Tool for PraisonAI Agents.

Generate images using AI models (OpenAI DALL-E, Stability AI, etc.).

Usage:
    from praisonai_tools import ImageTool
    
    # Using OpenAI DALL-E
    img = ImageTool()  # Uses OPENAI_API_KEY env var
    result = img.generate("A sunset over mountains")
    
    # With custom settings
    img = ImageTool(
        model="dall-e-3",
        size="1024x1024",
        quality="hd"
    )
    result = img.generate("A futuristic city")

Environment Variables:
    OPENAI_API_KEY: OpenAI API key for DALL-E
"""

import os
import logging
from typing import Any, Dict, Literal, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

# Valid sizes for different models
DALLE3_SIZES = ["1024x1024", "1792x1024", "1024x1792"]
DALLE2_SIZES = ["256x256", "512x512", "1024x1024"]


class ImageTool(BaseTool):
    """Tool for generating images using AI models.
    
    Supports OpenAI DALL-E 2 and DALL-E 3 for image generation.
    
    Attributes:
        name: Tool identifier
        description: Tool description for LLM
        model: Image model to use
        size: Image dimensions
        quality: Image quality (standard/hd)
        style: Image style (vivid/natural)
    """
    
    name = "image_generate"
    description = "Generate images from text descriptions using AI. Returns image URLs."
    
    def __init__(
        self,
        model: str = "dall-e-3",
        size: str = "1024x1024",
        quality: Literal["standard", "hd"] = "standard",
        style: Literal["vivid", "natural"] = "vivid",
        api_key: Optional[str] = None,
        save_path: Optional[str] = None,
    ):
        """Initialize ImageTool.
        
        Args:
            model: Model to use ("dall-e-3" or "dall-e-2")
            size: Image size (e.g., "1024x1024", "1792x1024")
            quality: "standard" or "hd" (DALL-E 3 only)
            style: "vivid" or "natural" (DALL-E 3 only)
            api_key: OpenAI API key (or use OPENAI_API_KEY env var)
            save_path: Optional directory to save generated images
        """
        self.model = model
        self.size = size
        self.quality = quality
        self.style = style
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.save_path = save_path
        self._client = None
        
        # Validate settings
        self._validate_settings()
        
        super().__init__()
    
    def _validate_settings(self):
        """Validate model and size combinations."""
        if self.model not in ["dall-e-3", "dall-e-2"]:
            raise ValueError(f"Invalid model: {self.model}. Use 'dall-e-3' or 'dall-e-2'.")
        
        if self.model == "dall-e-3" and self.size not in DALLE3_SIZES:
            raise ValueError(f"Invalid size for DALL-E 3: {self.size}. Use one of {DALLE3_SIZES}")
        
        if self.model == "dall-e-2" and self.size not in DALLE2_SIZES:
            raise ValueError(f"Invalid size for DALL-E 2: {self.size}. Use one of {DALLE2_SIZES}")
    
    @property
    def client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY not configured. Set OPENAI_API_KEY environment variable.")
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError("openai not installed. Install with: pip install openai")
            self._client = OpenAI(api_key=self.api_key)
        return self._client
    
    def run(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        style: Optional[str] = None,
        n: int = 1,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """Generate an image from a text prompt.
        
        Args:
            prompt: Text description of the image to generate
            size: Override default size
            quality: Override default quality
            style: Override default style
            n: Number of images (only 1 for DALL-E 3)
            
        Returns:
            Image URL(s) or error message
        """
        return self.generate(
            prompt=prompt,
            size=size,
            quality=quality,
            style=style,
            n=n
        )
    
    def generate(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        style: Optional[str] = None,
        n: int = 1,
    ) -> Dict[str, Any]:
        """Generate an image from a text prompt.
        
        Args:
            prompt: Text description of the image
            size: Image size (overrides default)
            quality: Image quality (overrides default)
            style: Image style (overrides default)
            n: Number of images to generate
            
        Returns:
            Dict with image URLs and metadata
        """
        if not prompt:
            return {"error": "Prompt is required"}
        
        if not self.api_key:
            return {"error": "OPENAI_API_KEY not configured"}
        
        # Use defaults if not specified
        size = size or self.size
        quality = quality or self.quality
        style = style or self.style
        
        # DALL-E 3 only supports n=1
        if self.model == "dall-e-3" and n > 1:
            logger.warning("DALL-E 3 only supports n=1. Setting n=1.")
            n = 1
        
        try:
            logger.info(f"Generating image with prompt: {prompt[:50]}...")
            
            kwargs = {
                "prompt": prompt,
                "model": self.model,
                "size": size,
                "n": n,
            }
            
            # DALL-E 3 specific options
            if self.model == "dall-e-3":
                kwargs["quality"] = quality
                kwargs["style"] = style
            
            response = self.client.images.generate(**kwargs)
            
            images = []
            for img in response.data:
                image_data = {
                    "url": img.url,
                    "revised_prompt": getattr(img, "revised_prompt", None),
                }
                images.append(image_data)
                
                # Save image if path specified
                if self.save_path and img.url:
                    self._save_image(img.url, prompt)
            
            return {
                "success": True,
                "model": self.model,
                "prompt": prompt,
                "images": images,
                "count": len(images),
            }
            
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return {"error": str(e)}
    
    def _save_image(self, url: str, prompt: str) -> Optional[str]:
        """Save image from URL to local file.
        
        Args:
            url: Image URL
            prompt: Original prompt (for filename)
            
        Returns:
            Local file path or None
        """
        try:
            import requests
            import hashlib
            from datetime import datetime
            
            # Create filename from prompt hash
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"image_{timestamp}_{prompt_hash}.png"
            
            filepath = os.path.join(self.save_path, filename)
            os.makedirs(self.save_path, exist_ok=True)
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(filepath, "wb") as f:
                f.write(response.content)
            
            logger.info(f"Image saved to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            return None
    
    def edit(
        self,
        image_path: str,
        prompt: str,
        mask_path: Optional[str] = None,
        size: str = "1024x1024",
        n: int = 1,
    ) -> Dict[str, Any]:
        """Edit an existing image (DALL-E 2 only).
        
        Args:
            image_path: Path to the image to edit
            prompt: Description of the edit
            mask_path: Optional mask image (transparent areas will be edited)
            size: Output size
            n: Number of variations
            
        Returns:
            Dict with edited image URLs
        """
        if self.model != "dall-e-2":
            return {"error": "Image editing is only supported with DALL-E 2"}
        
        if not os.path.exists(image_path):
            return {"error": f"Image not found: {image_path}"}
        
        try:
            kwargs = {
                "image": open(image_path, "rb"),
                "prompt": prompt,
                "size": size,
                "n": n,
            }
            
            if mask_path and os.path.exists(mask_path):
                kwargs["mask"] = open(mask_path, "rb")
            
            response = self.client.images.edit(**kwargs)
            
            images = [{"url": img.url} for img in response.data]
            
            return {
                "success": True,
                "images": images,
                "count": len(images),
            }
            
        except Exception as e:
            logger.error(f"Image edit error: {e}")
            return {"error": str(e)}
    
    def variation(
        self,
        image_path: str,
        size: str = "1024x1024",
        n: int = 1,
    ) -> Dict[str, Any]:
        """Create variations of an image (DALL-E 2 only).
        
        Args:
            image_path: Path to the source image
            size: Output size
            n: Number of variations
            
        Returns:
            Dict with variation image URLs
        """
        if self.model != "dall-e-2":
            return {"error": "Image variations are only supported with DALL-E 2"}
        
        if not os.path.exists(image_path):
            return {"error": f"Image not found: {image_path}"}
        
        try:
            response = self.client.images.create_variation(
                image=open(image_path, "rb"),
                size=size,
                n=n,
            )
            
            images = [{"url": img.url} for img in response.data]
            
            return {
                "success": True,
                "images": images,
                "count": len(images),
            }
            
        except Exception as e:
            logger.error(f"Image variation error: {e}")
            return {"error": str(e)}


# Convenience function
def generate_image(
    prompt: str,
    model: str = "dall-e-3",
    size: str = "1024x1024",
    quality: str = "standard",
    style: str = "vivid",
) -> Dict[str, Any]:
    """Generate an image using environment credentials.
    
    Args:
        prompt: Text description of the image
        model: Model to use
        size: Image size
        quality: Image quality
        style: Image style
        
    Returns:
        Dict with image URL and metadata
    """
    tool = ImageTool(model=model, size=size, quality=quality, style=style)
    return tool.generate(prompt=prompt)
