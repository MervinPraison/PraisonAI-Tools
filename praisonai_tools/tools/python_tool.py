"""Python Tool for PraisonAI Agents.

Execute Python code locally.

Usage:
    from praisonai_tools import PythonTool
    
    python = PythonTool()
    result = python.execute("print('Hello')")
"""

import logging
import sys
from io import StringIO
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class PythonTool(BaseTool):
    """Tool for Python code execution."""
    
    name = "python"
    description = "Execute Python code locally."
    
    def __init__(self, safe_mode: bool = True):
        self.safe_mode = safe_mode
        super().__init__()
    
    def run(
        self,
        action: str = "execute",
        code: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "execute":
            return self.execute(code=code)
        elif action == "eval":
            return self.eval_expr(expr=code)
        return {"error": f"Unknown action: {action}"}
    
    def execute(self, code: str) -> Dict[str, Any]:
        """Execute Python code."""
        if not code:
            return {"error": "code is required"}
        
        if self.safe_mode:
            forbidden = ["import os", "import sys", "subprocess", "eval(", "exec(", "__import__"]
            for f in forbidden:
                if f in code:
                    return {"error": f"Forbidden pattern: {f}"}
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        try:
            exec_globals = {"__builtins__": __builtins__}
            exec(code, exec_globals)
            stdout = sys.stdout.getvalue()
            stderr = sys.stderr.getvalue()
            return {"stdout": stdout, "stderr": stderr, "success": True}
        except Exception as e:
            stderr = sys.stderr.getvalue()
            return {"error": str(e), "stderr": stderr}
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    def eval_expr(self, expr: str) -> Dict[str, Any]:
        """Evaluate Python expression."""
        if not expr:
            return {"error": "expr is required"}
        
        try:
            result = eval(expr, {"__builtins__": {}})
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}


def python_execute(code: str) -> Dict[str, Any]:
    """Execute Python code."""
    return PythonTool().execute(code=code)
