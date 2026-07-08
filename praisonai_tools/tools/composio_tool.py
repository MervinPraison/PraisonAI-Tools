"""Composio integration tools for PraisonAI Agents.

Composio provides 250+ managed app integrations exposed as agent-callable tools.

Requires: pip install praisonai-tools[composio]
Environment: COMPOSIO_API_KEY

Usage:
    from praisonaiagents import Agent
    from praisonai_tools import composio_tools

    agent = Agent(name="dev", tools=composio_tools(apps=["github"]))
    agent.start("Star the praisonai/PraisonAI repository")
"""

import logging
import os
from importlib import util
from typing import Any, Callable, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


def _check_composio_available(api_key: Optional[str] = None) -> tuple[bool, Optional[str]]:
    """Return (is_available, error_message).

    ``api_key`` takes precedence over the ``COMPOSIO_API_KEY`` environment
    variable so callers who pass a key explicitly are not forced to also set
    the env var.
    """
    if util.find_spec("composio") is None:
        return False, "composio package is not installed. Install with: pip install praisonai-tools[composio]"

    if not api_key and not os.environ.get("COMPOSIO_API_KEY"):
        return False, (
            "COMPOSIO_API_KEY environment variable is not set. "
            "Please set it to use Composio tools."
        )

    return True, None


class ComposioTools:
    """Composio managed-integration tools for Agent(tools=[...])."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("COMPOSIO_API_KEY")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from composio import Composio

                self._client = Composio(api_key=self.api_key)
            except ImportError:
                from composio import ComposioToolSet

                self._client = ComposioToolSet(api_key=self.api_key)
        return self._client

    def get_tools(
        self,
        apps: Optional[List[str]] = None,
        actions: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ) -> List[Callable]:
        """Fetch Composio tools as agent-callable Python functions."""
        is_available, error = _check_composio_available(self.api_key)
        if not is_available:
            logger.error(error)
            return []

        try:
            client = self._get_client()

            if hasattr(client, "tools") and hasattr(client.tools, "get"):
                # Composio v3 SDK: `apps` -> `toolkits`, `user_id` required.
                # The API key is an auth credential, not an entity identifier,
                # so never use it as a user_id fallback.
                kwargs: Dict[str, Any] = {"user_id": user_id or "default"}
                if apps:
                    kwargs["toolkits"] = apps
                if actions:
                    kwargs["tools"] = actions
                if tags:
                    kwargs["tags"] = tags
                tools = client.tools.get(**kwargs)
            else:
                # Legacy ComposioToolSet SDK.
                toolset_kwargs: Dict[str, Any] = {}
                if apps:
                    toolset_kwargs["apps"] = apps
                if actions:
                    toolset_kwargs["actions"] = actions
                if tags:
                    toolset_kwargs["tags"] = tags
                tools = client.get_tools(**toolset_kwargs)

            return list(tools) if tools else []

        except Exception as e:
            logger.error(f"Composio get_tools error: {e}")
            return []

    def list_apps(self) -> List[str]:
        """List available Composio app slugs."""
        is_available, error = _check_composio_available(self.api_key)
        if not is_available:
            logger.error(error)
            return []

        try:
            client = self._get_client()

            if hasattr(client, "apps") and hasattr(client.apps, "get"):
                apps = client.apps.get()
            elif hasattr(client, "get_apps"):
                apps = client.get_apps()
            else:
                return []

            result = []
            for app in apps or []:
                if isinstance(app, str):
                    slug = app
                elif isinstance(app, dict):
                    slug = app.get("key") or app.get("name") or app.get("slug")
                else:
                    slug = (
                        getattr(app, "key", None)
                        or getattr(app, "name", None)
                        or getattr(app, "slug", None)
                    )
                if slug:
                    result.append(slug)
            return result

        except Exception as e:
            logger.error(f"Composio list_apps error: {e}")
            return []


def composio_tools(
    apps: Optional[List[str]] = None,
    actions: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> List[Callable]:
    """Load Composio tools as agent-callable Python functions."""
    return ComposioTools(api_key=api_key).get_tools(
        apps=apps, actions=actions, tags=tags, user_id=user_id
    )


def composio_list_apps(api_key: Optional[str] = None) -> List[str]:
    """List available Composio app slugs."""
    return ComposioTools(api_key=api_key).list_apps()


class ComposioTool(BaseTool):
    """Single-tool wrapper for explicit Composio action execution."""

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
                raise ImportError(
                    "composio not installed. Install with: pip install praisonai-tools[composio]"
                )
            self._toolset = ComposioToolSet(api_key=self.api_key)
        return self._toolset

    def run(
        self,
        action: str = "execute",
        action_name: Optional[str] = None,
        params: Optional[Dict] = None,
        **kwargs,
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        if action == "execute":
            return self.execute(action_name=action_name, params=params or kwargs)
        if action == "list_actions":
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
    """Execute a Composio action."""
    return ComposioTool().execute(action_name=action_name, params=params)
