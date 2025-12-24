"""Composio Tool for PraisonAI Agents.

Execute actions via Composio integrations.

Usage:
    from praisonai_tools import ComposioTool
    
    composio = ComposioTool()
    result = composio.execute("GITHUB_CREATE_ISSUE", {"repo": "owner/repo", "title": "Bug"})

Environment Variables:
    COMPOSIO_API_KEY: Composio API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ComposioTool(BaseTool):
    """Tool for Composio integrations."""
    
    name = "composio"
    description = "Execute actions via Composio integrations."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("COMPOSIO_API_KEY")
        self._toolset = None
        super().__init__()
    
    @property
    def toolset(self):
        if self._toolset is None:
            try:
                from composio import ComposioToolSet
            except ImportError:
                raise ImportError("composio-core not installed. Install with: pip install composio-core")
            self._toolset = ComposioToolSet(api_key=self.api_key)
        return self._toolset
    
    def run(
        self,
        action: str = "execute",
        action_name: Optional[str] = None,
        params: Optional[Dict] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        if action == "execute":
            return self.execute(action_name=action_name, params=params or kwargs)
        elif action == "list_actions":
            return self.list_actions(app=kwargs.get("app"))
        return {"error": f"Unknown action: {action}"}
    
    def execute(self, action_name: str, params: Dict = None) -> Dict[str, Any]:
        """Execute a Composio action."""
        if not action_name:
            return {"error": "action_name is required"}
        
        try:
            result = self.toolset.execute_action(action_name, params or {})
            return {"result": result}
        except Exception as e:
            logger.error(f"Composio execute error: {e}")
            return {"error": str(e)}
    
    def list_actions(self, app: str = None) -> List[Dict[str, Any]]:
        """List available actions."""
        try:
            if app:
                actions = self.toolset.get_actions(apps=[app])
            else:
                actions = self.toolset.get_actions()
            return [{"name": a.name, "description": a.description} for a in actions]
        except Exception as e:
            logger.error(f"Composio list_actions error: {e}")
            return [{"error": str(e)}]


def composio_execute(action_name: str, params: Dict = None) -> Dict[str, Any]:
    """Execute Composio action."""
    return ComposioTool().execute(action_name=action_name, params=params)
