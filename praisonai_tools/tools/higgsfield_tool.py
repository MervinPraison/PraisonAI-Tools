"""Higgsfield AI Tool for PraisonAI Agents.

AI video/image generation using Higgsfield Cloud.

Usage:
    from praisonai_tools import HiggsfieldTool
    
    hf = HiggsfieldTool()
    result = hf.generate("A sunset over mountains", model="bytedance/seedream/v4/text-to-image")

Environment Variables:
    HF_KEY: Higgsfield API key in format "api-key:api-secret"
    HF_API_KEY: Higgsfield API key (alternative)
    HF_API_SECRET: Higgsfield API secret (alternative)
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class HiggsfieldTool(BaseTool):
    """Tool for Higgsfield AI video/image generation."""
    
    name = "higgsfield"
    description = "AI video/image generation using Higgsfield Cloud."
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        # Handle HF_KEY format "api-key:api-secret"
        hf_key = os.getenv("HF_KEY")
        if hf_key and ":" in hf_key:
            key_parts = hf_key.split(":", 1)
            self.api_key = api_key or key_parts[0]
            self.api_secret = api_secret or key_parts[1]
        else:
            self.api_key = api_key or os.getenv("HF_API_KEY") or hf_key
            self.api_secret = api_secret or os.getenv("HF_API_SECRET")
        super().__init__()
    
    def run(
        self,
        action: str = "generate",
        prompt: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "generate":
            return self.generate(prompt=prompt, **kwargs)
        elif action == "status":
            return self.get_status(request_id=kwargs.get("request_id"))
        elif action == "upload":
            return self.upload_file(file_path=kwargs.get("file_path"))
        return {"error": f"Unknown action: {action}"}
    
    def generate(
        self,
        prompt: str,
        model: str = "bytedance/seedream/v4/text-to-image",
        resolution: str = "2K",
        aspect_ratio: str = "16:9",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate AI image/video from prompt."""
        if not prompt:
            return {"error": "prompt is required"}
        if not self.api_key or not self.api_secret:
            return {"error": "HF_KEY or HF_API_KEY + HF_API_SECRET required"}
        
        try:
            import higgsfield_client
        except ImportError:
            return {"error": "higgsfield-client not installed. Install with: pip install higgsfield-client"}
        
        try:
            # Set up auth
            if os.getenv("HF_KEY"):
                os.environ["HF_KEY"] = f"{self.api_key}:{self.api_secret}"
            else:
                os.environ["HF_API_KEY"] = self.api_key
                os.environ["HF_API_SECRET"] = self.api_secret
            
            arguments = {
                "prompt": prompt,
                "resolution": resolution,
                "aspect_ratio": aspect_ratio,
                **kwargs
            }
            
            # Submit and wait (blocking)
            result = higgsfield_client.subscribe(model, arguments=arguments)
            return result
        except Exception as e:
            logger.error(f"Higgsfield generate error: {e}")
            return {"error": str(e)}
    
    def get_status(self, request_id: str) -> Dict[str, Any]:
        """Check Higgsfield generation status."""
        if not request_id:
            return {"error": "request_id is required"}
        if not self.api_key or not self.api_secret:
            return {"error": "HF_KEY or HF_API_KEY + HF_API_SECRET required"}
        
        try:
            import higgsfield_client
        except ImportError:
            return {"error": "higgsfield-client not installed. Install with: pip install higgsfield-client"}
        
        try:
            # Set up auth
            if os.getenv("HF_KEY"):
                os.environ["HF_KEY"] = f"{self.api_key}:{self.api_secret}"
            else:
                os.environ["HF_API_KEY"] = self.api_key
                os.environ["HF_API_SECRET"] = self.api_secret
            
            # Poll status - this is a simplified version
            # In practice, you'd need to implement proper request tracking
            return {"error": "Status checking requires request controller from original submit call"}
        except Exception as e:
            logger.error(f"Higgsfield status error: {e}")
            return {"error": str(e)}
    
    def upload_file(self, file_path: str) -> Union[str, Dict[str, Any]]:
        """Upload file to Higgsfield for image-to-video."""
        if not file_path:
            return {"error": "file_path is required"}
        if not self.api_key or not self.api_secret:
            return {"error": "HF_KEY or HF_API_KEY + HF_API_SECRET required"}
        
        try:
            import higgsfield_client
        except ImportError:
            return {"error": "higgsfield-client not installed. Install with: pip install higgsfield-client"}
        
        try:
            # Set up auth
            if os.getenv("HF_KEY"):
                os.environ["HF_KEY"] = f"{self.api_key}:{self.api_secret}"
            else:
                os.environ["HF_API_KEY"] = self.api_key
                os.environ["HF_API_SECRET"] = self.api_secret
            
            url = higgsfield_client.upload_file(file_path)
            return url
        except Exception as e:
            logger.error(f"Higgsfield upload error: {e}")
            return {"error": str(e)}


def higgsfield_generate(
    prompt: str,
    model: str = "bytedance/seedream/v4/text-to-image",
    resolution: str = "2K",
    aspect_ratio: str = "16:9"
) -> Dict[str, Any]:
    """Generate AI image/video with Higgsfield."""
    return HiggsfieldTool().generate(
        prompt=prompt,
        model=model,
        resolution=resolution,
        aspect_ratio=aspect_ratio
    )


def higgsfield_status(request_id: str) -> Dict[str, Any]:
    """Check Higgsfield generation status."""
    return HiggsfieldTool().get_status(request_id=request_id)


def higgsfield_upload(file_path: str) -> Union[str, Dict[str, Any]]:
    """Upload file to Higgsfield for image-to-video."""
    return HiggsfieldTool().upload_file(file_path=file_path)