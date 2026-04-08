"""Pinchwork Tool for PraisonAI Agents.

Agent-to-agent task delegation using Pinchwork marketplace.

Usage:
    from praisonai_tools import PinchworkTool
    
    tool = PinchworkTool()
    result = tool.delegate("Analyze this data", skills_required=["python", "data-analysis"], budget=50.0)

Environment Variables:
    PINCHWORK_API_KEY: Pinchwork API key (optional)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class PinchworkTool(BaseTool):
    """Tool for Pinchwork agent marketplace delegation."""
    
    name = "pinchwork"
    description = "Delegate tasks to agent marketplace using Pinchwork."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PINCHWORK_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "delegate",
        task: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "delegate":
            return self.delegate(
                task=task,
                skills_required=kwargs.get("skills_required"),
                budget=kwargs.get("budget", 0.0)
            )
        return {"error": f"Unknown action: {action}"}
    
    def delegate(
        self,
        task: str,
        skills_required: Optional[List[str]] = None,
        budget: float = 0.0
    ) -> str:
        """Delegate a task to the Pinchwork agent marketplace.
        
        Args:
            task: Description of the task to delegate
            skills_required: List of required skills for the agent (optional)
            budget: Maximum budget for the task (default: 0.0)
        
        Returns:
            Result from the marketplace agent that completed the task
        """
        if not task:
            return "Error: task is required"
        
        try:
            import httpx
        except ImportError:
            return (
                "Error: httpx is required for Pinchwork integration. "
                "Install with: pip install praisonai-tools[marketplace] or pip install httpx"
            )
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post("https://api.pinchwork.com/delegate", json={
                    "task": task,
                    "skills": skills_required or [],
                    "budget": budget,
                    "api_key": self.api_key
                })
                response.raise_for_status()
                
                data = response.json()
                return data.get("result", "No result returned from marketplace")
                
        except httpx.RequestError as e:
            logger.error(f"Pinchwork request error: {e}")
            return f"Error connecting to Pinchwork: {e}"
        except httpx.HTTPStatusError as e:
            logger.error(f"Pinchwork API error: {e.response.status_code}")
            return f"Pinchwork API error ({e.response.status_code}): {e.response.text}"
        except Exception as e:
            logger.error(f"Pinchwork unexpected error: {e}")
            return f"Unexpected error during task delegation: {e}"


def pinchwork_delegate(task: str, skills_required: Optional[List[str]] = None, budget: float = 0.0) -> str:
    """Delegate a task to the Pinchwork agent marketplace."""
    return PinchworkTool().delegate(task=task, skills_required=skills_required, budget=budget)