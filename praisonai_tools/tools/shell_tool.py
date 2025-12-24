"""Shell Tool for PraisonAI Agents.

Execute shell commands.

Usage:
    from praisonai_tools import ShellTool
    
    shell = ShellTool()
    result = shell.execute("ls -la")
"""

import subprocess
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ShellTool(BaseTool):
    """Tool for executing shell commands."""
    
    name = "shell"
    description = "Execute shell commands and return output."
    
    def __init__(
        self,
        working_dir: Optional[str] = None,
        timeout: int = 60,
    ):
        self.working_dir = working_dir
        self.timeout = timeout
        super().__init__()
    
    def run(
        self,
        action: str = "execute",
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        action = action.lower().replace("-", "_")
        
        if action == "execute":
            return self.execute(command=command, args=args)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def execute(
        self,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        tail: int = 100,
    ) -> Dict[str, Any]:
        """Execute a shell command."""
        if not command and not args:
            return {"error": "command or args is required"}
        
        try:
            if args:
                cmd = args
            else:
                cmd = command
                
            result = subprocess.run(
                cmd,
                shell=isinstance(cmd, str),
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=self.timeout,
            )
            
            stdout = result.stdout
            if tail and stdout:
                lines = stdout.split("\n")
                stdout = "\n".join(lines[-tail:])
            
            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": stdout,
                "stderr": result.stderr if result.returncode != 0 else "",
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {self.timeout}s"}
        except Exception as e:
            logger.error(f"Shell execute error: {e}")
            return {"error": str(e)}


def shell_execute(command: str) -> Dict[str, Any]:
    """Execute shell command."""
    return ShellTool().execute(command=command)
