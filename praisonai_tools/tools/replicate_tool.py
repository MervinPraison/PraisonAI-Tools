"""Replicate Tool for PraisonAI Agents.

Run ML models on Replicate.

Usage:
    from praisonai_tools import ReplicateTool
    
    rep = ReplicateTool()
    output = rep.run_model("stability-ai/sdxl", {"prompt": "a cat"})

Environment Variables:
    REPLICATE_API_TOKEN: Replicate API token
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ReplicateTool(BaseTool):
    """Tool for Replicate ML models."""
    
    name = "replicate"
    description = "Run ML models on Replicate."
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
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
        if not self.api_token:
            return {"error": "REPLICATE_API_TOKEN required"}
        
        try:
            import replicate
        except ImportError:
            return {"error": "replicate not installed. Install with: pip install replicate"}
        
        try:
            output = replicate.run(model, input=input_data)
            if hasattr(output, "__iter__") and not isinstance(output, (str, dict)):
                output = list(output)
            return {"output": output}
        except Exception as e:
            logger.error(f"Replicate run_model error: {e}")
            return {"error": str(e)}


def replicate_run(model: str, input_data: Dict) -> Dict[str, Any]:
    """Run model on Replicate."""
    return ReplicateTool().run_model(model=model, input_data=input_data)
