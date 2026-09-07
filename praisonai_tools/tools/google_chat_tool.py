"""Google Chat Tool for PraisonAI Agents.

Send messages and manage Google Chat spaces via the Chat API. Also supports
incoming-webhook messages which require **no** OAuth/service-account auth — just
the webhook URL.

Usage:
    from praisonai_tools import GoogleChatTool

    chat = GoogleChatTool()
    chat.send_message("spaces/AAAA1234", "Deployment finished")

    # Webhook (no auth needed):
    chat.create_webhook_message("https://chat.googleapis.com/v1/...", "Hi")

Auth:
    Space/message operations share :class:`GoogleWorkspaceAuth`
    (Service Account / OAuth / ADC). ``create_webhook_message`` needs no auth.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool
from praisonai_tools.tools._google_auth import GoogleWorkspaceAuth, resolve_auth

logger = logging.getLogger(__name__)


class GoogleChatTool(BaseTool):
    """Tool for Google Chat spaces and messages."""

    name = "google_chat"
    description = "Send messages and manage Google Chat spaces (incl. webhooks)."

    def __init__(
        self,
        auth: Optional[GoogleWorkspaceAuth] = None,
        service_account_file: Optional[str] = None,
        credentials_file: Optional[str] = None,
        token_file: Optional[str] = None,
    ):
        self._auth = resolve_auth(
            auth,
            ["chat"],
            service_account_file=service_account_file,
            credentials_file=credentials_file,
            token_file=token_file,
        )
        self._service = None
        super().__init__()

    @property
    def service(self):
        if self._service is None:
            self._service = self._auth.build_service("chat", "v1", ["chat"])
        return self._service

    def run(self, action: str = "list_spaces", **kwargs) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        actions = {
            "list_spaces": lambda: self.list_spaces(),
            "get_space": lambda: self.get_space(space_name=kwargs.get("space_name")),
            "send_message": lambda: self.send_message(**kwargs),
            "list_messages": lambda: self.list_messages(**kwargs),
            "webhook": lambda: self.create_webhook_message(
                webhook_url=kwargs.get("webhook_url"), text=kwargs.get("text")
            ),
        }
        handler = actions.get(action)
        if handler:
            return handler()
        return {"error": f"Unknown action: {action}. Available: {', '.join(actions)}"}

    def list_spaces(self) -> List[Dict[str, Any]]:
        """List Chat spaces the caller is a member of."""
        try:
            result = self.service.spaces().list().execute()
            return [
                {
                    "name": s.get("name"),
                    "type": s.get("type") or s.get("spaceType"),
                    "displayName": s.get("displayName"),
                }
                for s in result.get("spaces", [])
            ]
        except Exception as e:
            logger.error(f"Google Chat list_spaces error: {e}")
            return [{"error": str(e)}]

    def get_space(self, space_name: str) -> Dict[str, Any]:
        """Get details of a single space (e.g. ``spaces/AAAA1234``)."""
        if not space_name:
            return {"error": "space_name is required"}
        try:
            return self.service.spaces().get(name=space_name).execute()
        except Exception as e:
            logger.error(f"Google Chat get_space error: {e}")
            return {"error": str(e)}

    def send_message(
        self, space_name: str, text: str, thread_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a text message to a space, optionally into a thread."""
        if not space_name or text is None:
            return {"error": "space_name and text are required"}
        try:
            kwargs: Dict[str, Any] = {"parent": space_name, "body": {"text": text}}
            if thread_key:
                kwargs["threadKey"] = thread_key
            message = self.service.spaces().messages().create(**kwargs).execute()
            return {"success": True, "name": message.get("name")}
        except Exception as e:
            logger.error(f"Google Chat send_message error: {e}")
            return {"error": str(e)}

    def list_messages(
        self, space_name: str, filter_str: Optional[str] = None, page_size: int = 25
    ) -> List[Dict[str, Any]]:
        """List messages in a space."""
        if not space_name:
            return [{"error": "space_name is required"}]
        try:
            kwargs: Dict[str, Any] = {"parent": space_name, "pageSize": page_size}
            if filter_str:
                kwargs["filter"] = filter_str
            result = self.service.spaces().messages().list(**kwargs).execute()
            return [
                {
                    "name": m.get("name"),
                    "text": m.get("text"),
                    "createTime": m.get("createTime"),
                }
                for m in result.get("messages", [])
            ]
        except Exception as e:
            logger.error(f"Google Chat list_messages error: {e}")
            return [{"error": str(e)}]

    def create_webhook_message(self, webhook_url: str, text: str) -> Dict[str, Any]:
        """Post a message via an incoming webhook URL (no auth required)."""
        if not webhook_url or text is None:
            return {"error": "webhook_url and text are required"}
        try:
            import json
            import urllib.request

            data = json.dumps({"text": text}).encode("utf-8")
            request = urllib.request.Request(
                webhook_url, data=data, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(request) as response:
                status = response.getcode()
            return {"success": True, "status": status}
        except Exception as e:
            logger.error(f"Google Chat webhook error: {e}")
            return {"error": str(e)}


def send_google_chat_webhook(webhook_url: str, text: str) -> Dict[str, Any]:
    """Send a Google Chat message via incoming webhook (no auth)."""
    return GoogleChatTool().create_webhook_message(webhook_url, text)
