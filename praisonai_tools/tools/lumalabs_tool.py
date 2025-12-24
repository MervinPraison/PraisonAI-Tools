"""LumaLabs Tool for PraisonAI Agents.

AI video generation using LumaLabs.

Usage:
    from praisonai_tools import LumaLabsTool
    
    luma = LumaLabsTool()
    video = luma.generate("A cat playing piano")

Environment Variables:
    LUMALABS_API_KEY: LumaLabs API key
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class LumaLabsTool(BaseTool):
    """Tool for LumaLabs video generation."""
    
    name = "lumalabs"
    description = "AI video generation using LumaLabs."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LUMALABS_API_KEY")
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
            return self.get_status(generation_id=kwargs.get("generation_id"))
        return {"error": f"Unknown action: {action}"}
    
    def generate(self, prompt: str, aspect_ratio: str = "16:9") -> Dict[str, Any]:
        """Generate video from prompt."""
        if not prompt:
            return {"error": "prompt is required"}
        if not self.api_key:
            return {"error": "LUMALABS_API_KEY required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {"prompt": prompt, "aspect_ratio": aspect_ratio}
            resp = requests.post(
                "https://api.lumalabs.ai/dream-machine/v1/generations",
                headers=headers,
                json=data,
                timeout=30,
            )
            return resp.json()
        except Exception as e:
            logger.error(f"LumaLabs generate error: {e}")
            return {"error": str(e)}
    
    def get_status(self, generation_id: str) -> Dict[str, Any]:
        """Get generation status."""
        if not generation_id:
            return {"error": "generation_id is required"}
        if not self.api_key:
            return {"error": "LUMALABS_API_KEY required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(
                f"https://api.lumalabs.ai/dream-machine/v1/generations/{generation_id}",
                headers=headers,
                timeout=10,
            )
            return resp.json()
        except Exception as e:
            logger.error(f"LumaLabs status error: {e}")
            return {"error": str(e)}


def lumalabs_generate(prompt: str) -> Dict[str, Any]:
    """Generate video with LumaLabs."""
    return LumaLabsTool().generate(prompt=prompt)
