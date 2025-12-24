"""Sleep Tool for PraisonAI Agents.

Pause execution for a specified duration.

Usage:
    from praisonai_tools import SleepTool
    
    sleep = SleepTool()
    sleep.wait(seconds=5)
"""

import logging
import time
from typing import Any, Dict, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SleepTool(BaseTool):
    """Tool for pausing execution."""
    
    name = "sleep"
    description = "Pause execution for a specified duration."
    
    def run(
        self,
        action: str = "wait",
        seconds: float = 1.0,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "wait":
            return self.wait(seconds=seconds)
        return {"error": f"Unknown action: {action}"}
    
    def wait(self, seconds: float = 1.0) -> Dict[str, Any]:
        """Wait for specified seconds."""
        if seconds < 0:
            return {"error": "seconds must be non-negative"}
        if seconds > 300:
            return {"error": "Maximum wait time is 300 seconds"}
        
        try:
            time.sleep(seconds)
            return {"success": True, "waited_seconds": seconds}
        except Exception as e:
            logger.error(f"Sleep error: {e}")
            return {"error": str(e)}


def sleep_wait(seconds: float = 1.0) -> Dict[str, Any]:
    """Wait for seconds."""
    return SleepTool().wait(seconds=seconds)
