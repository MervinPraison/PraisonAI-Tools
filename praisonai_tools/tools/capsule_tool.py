"""Capsule Tool for PraisonAI Agents.

Run untrusted Python code in local WebAssembly sandboxes.

Usage:
    from praisonai_tools import CapsuleTool

    capsule = CapsuleTool()
    result = capsule.run_code("print('Hello from Python')")
"""

import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


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
    ) -> Union[str, Dict[str, Any]]:
        if action == "run_code":
            return self.run_code(code=code)
        return {"error": f"Unknown action: {action}"}

    def run_code(self, code: str) -> Dict[str, Any]:
        """Run Python code in sandbox."""
        if not code:
            return {"error": "code is required"}

        try:
            from langchain_capsule import CapsulePythonTool
        except ImportError:
            return {"error": "langchain-capsule not installed. Install with: pip install langchain-capsule"}

        try:
            return CapsulePythonTool().run(code)
        except Exception as e:
            logger.error(f"Capsule Python execution error: {e}")
            return {"error": str(e)}


def capsule_run_code(code: str) -> Dict[str, Any]:
    """Run code in Capsule."""
    return CapsuleTool().run_code(code=code)

