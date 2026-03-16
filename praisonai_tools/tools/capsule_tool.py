"""Capsule Tool for PraisonAI Agents.

Run untrusted Python code in local WebAssembly sandboxes.

Usage:
    from praisonai_tools import CapsuleTool

    capsule = CapsuleTool()
    result = capsule.run_code("print('Hello from Python')")
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)
_capsule_tool_instance = None


class CapsuleTool(BaseTool):
    """Tool for sandboxed Python code execution."""

    name = "capsule"
    description: str = (
        "Execute Python code in a secure isolated WebAssembly sandbox. "
        "Both standard output (print statements) and the last evaluated expression are returned. "
        "Supports pure Python code only."
    )

    def run(
        self,
        action: str = "run_code",
        code: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        if action == "run_code":
            return self.run_code(code=code)
        elif action == "preload":
            return self.preload()
        return {"error": f"Unknown action: {action}"}

    def run_code(self, code: Optional[str] = None) -> Dict[str, Any]:
        """Run Python code in sandbox.

        Args:
            code: Python code to execute

        Returns:
            Dict with 'result' key (success) or 'error' key (failure)
        """
        if not code:
            return {"error": "code is required"}

        try:
            from capsule_adapter import run_python
        except ImportError:
            return {"error": "capsule_adapter not installed. Install with: pip install capsule-run-adapter"}

        try:
            result = asyncio.run(run_python(code))
            return {"result": result}
        except Exception as e:
            logger.error(f"Capsule Python execution error: {e}")
            return {"error": str(e)}

    def preload(self) -> Dict[str, Any]:
        """Preload Python sandbox for faster execution.

        Returns:
            Dict with 'status' and 'message' keys
        """
        try:
            from capsule_adapter import load_python_sandbox
        except ImportError:
            return {"error": "capsule_adapter not installed. Install with: pip install capsule-run-adapter"}

        try:
            asyncio.run(load_python_sandbox())
            return {"status": "success", "message": "Python sandbox preloaded successfully"}
        except Exception as e:
            logger.error(f"Capsule preload error: {e}")
            return {"error": str(e)}


def _get_capsule_tool() -> CapsuleTool:
    """Get or create the singleton CapsuleTool instance."""
    global _capsule_tool_instance
    if _capsule_tool_instance is None:
        _capsule_tool_instance = CapsuleTool()
    return _capsule_tool_instance


def capsule_run_code(code: str) -> Dict[str, Any]:
    """Run code in Capsule."""
    return _get_capsule_tool().run_code(code=code)
