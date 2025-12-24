"""Fal Tool for PraisonAI Agents.

Run AI models on Fal.ai.

Usage:
    from praisonai_tools import FalTool
    
    fal = FalTool()
    output = fal.run_model("fal-ai/flux/schnell", {"prompt": "a cat"})

Environment Variables:
    FAL_KEY: Fal API key
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class FalTool(BaseTool):
    """Tool for Fal.ai models."""
    
    name = "fal"
    description = "Run AI models on Fal.ai."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FAL_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "run_model",
        model: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "run_model":
            return self.run_model(model=model, input_data=kwargs.get("input_data", kwargs))
        return {"error": f"Unknown action: {action}"}
    
    def run_model(self, model: str, input_data: Dict) -> Dict[str, Any]:
        """Run a model."""
        if not model:
            return {"error": "model is required"}
        if not self.api_key:
            return {"error": "FAL_KEY required"}
        
        try:
            import fal_client
        except ImportError:
            return {"error": "fal-client not installed. Install with: pip install fal-client"}
        
        try:
            result = fal_client.subscribe(model, arguments=input_data)
            return {"output": result}
        except Exception as e:
            logger.error(f"Fal run_model error: {e}")
            return {"error": str(e)}


def fal_run(model: str, input_data: Dict) -> Dict[str, Any]:
    """Run model on Fal."""
    return FalTool().run_model(model=model, input_data=input_data)
