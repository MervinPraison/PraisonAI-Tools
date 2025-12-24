"""E2B Tool for PraisonAI Agents.

Run code in E2B sandboxes.

Usage:
    from praisonai_tools import E2BTool
    
    e2b = E2BTool()
    result = e2b.run_code("print('Hello')", language="python")

Environment Variables:
    E2B_API_KEY: E2B API key
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class E2BTool(BaseTool):
    """Tool for E2B code execution."""
    
    name = "e2b"
    description = "Run code in E2B sandboxes."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("E2B_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "run_code",
        code: Optional[str] = None,
        language: str = "python",
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "run_code":
            return self.run_code(code=code, language=language)
        return {"error": f"Unknown action: {action}"}
    
    def run_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Run code in sandbox."""
        if not code:
            return {"error": "code is required"}
        if not self.api_key:
            return {"error": "E2B_API_KEY required"}
        
        try:
            from e2b_code_interpreter import CodeInterpreter
        except ImportError:
            return {"error": "e2b-code-interpreter not installed. Install with: pip install e2b-code-interpreter"}
        
        try:
            with CodeInterpreter() as sandbox:
                execution = sandbox.notebook.exec_cell(code)
                return {
                    "stdout": execution.logs.stdout,
                    "stderr": execution.logs.stderr,
                    "results": [str(r) for r in execution.results],
                }
        except Exception as e:
            logger.error(f"E2B run_code error: {e}")
            return {"error": str(e)}


def e2b_run_code(code: str, language: str = "python") -> Dict[str, Any]:
    """Run code in E2B."""
    return E2BTool().run_code(code=code, language=language)
