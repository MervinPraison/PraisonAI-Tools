"""Signal Tool for PraisonAI Agents.

Send and receive messages via Signal using signal-cli REST API.

Usage:
    from praisonai_tools import SignalTool
    
    signal = SignalTool(base_url="http://localhost:8080")
    signal.send_message(to="+1234567890", message="Hello from AI!")

Environment Variables:
    SIGNAL_CLI_URL: Signal-cli REST API base URL (default: http://localhost:8080)
    SIGNAL_ACCOUNT: Your Signal phone number (e.g., +1234567890)

Setup:
    1. Run signal-cli in REST mode: https://github.com/bbernhard/signal-cli-rest-api
    2. Link your device or register a new number
    3. Set environment variables
"""

import os
import logging
import uuid
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


@dataclass
class SignalSendResult:
    """Result of sending a Signal message."""
    success: bool
    message_id: Optional[str] = None
    timestamp: Optional[int] = None
    error: Optional[str] = None


class SignalTool(BaseTool):
    """Tool for Signal messaging via signal-cli REST API.
    
    Supports:
    - Sending text messages to individuals and groups
    - Sending media attachments
    - Typing indicators
    - Read receipts
    - Reactions
    
    Based on moltbot's Signal implementation patterns.
    """
    
    name = "signal"
    description = "Send and receive messages via Signal messenger."
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        account: Optional[str] = None,
        timeout_ms: int = 10000,
    ):
        """Initialize SignalTool.
        
        Args:
            base_url: Signal-cli REST API URL (or use SIGNAL_CLI_URL env var)
            account: Your Signal phone number (or use SIGNAL_ACCOUNT env var)
            timeout_ms: Request timeout in milliseconds
        """
        self.base_url = self._normalize_base_url(
            base_url or os.getenv("SIGNAL_CLI_URL") or os.getenv("SIGNAL_BASE_URL") or "http://localhost:8080"
        )
        self.account = account or os.getenv("SIGNAL_ACCOUNT") or os.getenv("SIGNAL_PHONE_NUMBER")
        self.timeout_ms = timeout_ms
        super().__init__()
    
    def _normalize_base_url(self, url: str) -> str:
        """Normalize the base URL."""
        url = url.strip()
        if not url:
            return "http://localhost:8080"
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"
        return url.rstrip("/")
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to Signal-cli API."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. Install with: pip install requests"}
        
        timeout_sec = (timeout or self.timeout_ms) / 1000
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=timeout_sec)
            else:
                response = requests.post(
                    url,
                    json=data,
                    headers={"Content-Type": "application/json"},
                    timeout=timeout_sec,
                )
            
            if response.status_code == 201:
                return {"success": True}
            
            if not response.text:
                return {"error": f"Empty response (status {response.status_code})"}
            
            return response.json()
        except Exception as e:
            logger.error(f"Signal API error: {e}")
            return {"error": str(e)}
    
    def _rpc_request(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make JSON-RPC request to Signal-cli API."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        request_id = str(uuid.uuid4())
        body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id,
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/rpc",
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout_ms / 1000,
            )
            
            if response.status_code == 201:
                return {"success": True}
            
            result = response.json()
            if "error" in result:
                code = result["error"].get("code", "unknown")
                msg = result["error"].get("message", "Signal RPC error")
                return {"error": f"Signal RPC {code}: {msg}"}
            
            return result.get("result", {})
        except Exception as e:
            logger.error(f"Signal RPC error: {e}")
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "send",
        to: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """Execute Signal action.
        
        Args:
            action: "send", "send_typing", "send_receipt", "check", "list_groups"
            to: Recipient phone number or group ID
            message: Message text
        """
        action = action.lower().replace("-", "_")
        
        if action == "send":
            return self.send_message(to=to, message=message, **kwargs)
        elif action == "send_typing":
            return self.send_typing(to=to, **kwargs)
        elif action == "send_receipt":
            return self.send_read_receipt(to=to, **kwargs)
        elif action == "check":
            return self.check_connection()
        elif action == "list_groups":
            return self.list_groups()
        elif action == "send_reaction":
            return self.send_reaction(to=to, **kwargs)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def _parse_target(self, to: str) -> Dict[str, Any]:
        """Parse recipient target string.
        
        Supports:
        - Phone numbers: +1234567890
        - Groups: group:abc123
        - Usernames: username:alice or u:alice
        """
        value = to.strip()
        if not value:
            return {"error": "Recipient is required"}
        
        # Remove signal: prefix if present
        if value.lower().startswith("signal:"):
            value = value[7:].strip()
        
        lower = value.lower()
        
        if lower.startswith("group:"):
            return {"type": "group", "groupId": value[6:].strip()}
        elif lower.startswith("username:"):
            return {"type": "username", "username": [value[9:].strip()]}
        elif lower.startswith("u:"):
            return {"type": "username", "username": [value[2:].strip()]}
        else:
            return {"type": "recipient", "recipient": [value]}
    
    def send_message(
        self,
        to: str,
        message: str,
        media_url: Optional[str] = None,
        text_mode: str = "markdown",
    ) -> Dict[str, Any]:
        """Send a text message via Signal.
        
        Args:
            to: Recipient phone number, group ID, or username
            message: Message text
            media_url: Optional URL to media attachment
            text_mode: "markdown" or "plain"
            
        Returns:
            Send result with message_id and timestamp
        """
        if not to:
            return {"error": "Recipient (to) is required"}
        if not message and not media_url:
            return {"error": "Message or media_url is required"}
        
        target = self._parse_target(to)
        if "error" in target:
            return target
        
        params: Dict[str, Any] = {"message": message or ""}
        
        if self.account:
            params["account"] = self.account
        
        # Add target parameters
        target_type = target.pop("type")
        params.update(target)
        
        # Handle attachments
        if media_url:
            params["attachments"] = [media_url]
        
        result = self._rpc_request("send", params)
        
        if "error" in result:
            return result
        
        timestamp = result.get("timestamp")
        return {
            "success": True,
            "message_id": str(timestamp) if timestamp else "unknown",
            "timestamp": timestamp,
        }
    
    def send_typing(self, to: str, stop: bool = False) -> Dict[str, Any]:
        """Send typing indicator.
        
        Args:
            to: Recipient phone number or group ID
            stop: If True, stop typing indicator
            
        Returns:
            Success status
        """
        if not to:
            return {"error": "Recipient (to) is required"}
        
        target = self._parse_target(to)
        if "error" in target:
            return target
        
        params: Dict[str, Any] = {}
        if self.account:
            params["account"] = self.account
        if stop:
            params["stop"] = True
        
        target.pop("type")
        params.update(target)
        
        result = self._rpc_request("sendTyping", params)
        return {"success": True} if "error" not in result else result
    
    def send_read_receipt(
        self,
        to: str,
        target_timestamp: int,
        receipt_type: str = "read",
    ) -> Dict[str, Any]:
        """Send read receipt for a message.
        
        Args:
            to: Sender's phone number
            target_timestamp: Timestamp of the message to acknowledge
            receipt_type: "read" or "viewed"
            
        Returns:
            Success status
        """
        if not to:
            return {"error": "Recipient (to) is required"}
        if not target_timestamp or target_timestamp <= 0:
            return {"error": "Valid target_timestamp is required"}
        
        target = self._parse_target(to)
        if "error" in target:
            return target
        
        params: Dict[str, Any] = {
            "targetTimestamp": target_timestamp,
            "type": receipt_type,
        }
        if self.account:
            params["account"] = self.account
        
        target.pop("type")
        params.update(target)
        
        result = self._rpc_request("sendReceipt", params)
        return {"success": True} if "error" not in result else result
    
    def send_reaction(
        self,
        to: str,
        emoji: str,
        target_author: str,
        target_timestamp: int,
        remove: bool = False,
    ) -> Dict[str, Any]:
        """Send a reaction to a message.
        
        Args:
            to: Chat where the message is (phone number or group ID)
            emoji: Reaction emoji
            target_author: Author of the message to react to
            target_timestamp: Timestamp of the message
            remove: If True, remove the reaction
            
        Returns:
            Success status
        """
        if not to or not emoji or not target_author or not target_timestamp:
            return {"error": "to, emoji, target_author, and target_timestamp are required"}
        
        target = self._parse_target(to)
        if "error" in target:
            return target
        
        params: Dict[str, Any] = {
            "emoji": emoji,
            "targetAuthor": target_author,
            "targetTimestamp": target_timestamp,
            "remove": remove,
        }
        if self.account:
            params["account"] = self.account
        
        target.pop("type")
        params.update(target)
        
        result = self._rpc_request("sendReaction", params)
        return {"success": True} if "error" not in result else result
    
    def check_connection(self) -> Dict[str, Any]:
        """Check if Signal-cli API is reachable.
        
        Returns:
            Connection status
        """
        result = self._request("GET", "/api/v1/check")
        if "error" in result:
            return {"ok": False, "error": result["error"]}
        return {"ok": True, "status": "connected"}
    
    def list_groups(self) -> List[Dict[str, Any]]:
        """List all Signal groups.
        
        Returns:
            List of groups
        """
        if not self.account:
            return [{"error": "SIGNAL_ACCOUNT is required"}]
        
        result = self._rpc_request("listGroups", {"account": self.account})
        if "error" in result:
            return [result]
        
        groups = result if isinstance(result, list) else []
        return [
            {
                "id": g.get("id"),
                "name": g.get("name"),
                "members": g.get("members", []),
            }
            for g in groups
        ]


def send_signal_message(to: str, message: str) -> Dict[str, Any]:
    """Send a Signal message.
    
    Args:
        to: Recipient phone number or group ID
        message: Message text
        
    Returns:
        Send result
    """
    return SignalTool().send_message(to=to, message=message)


def check_signal_connection() -> Dict[str, Any]:
    """Check Signal-cli connection status."""
    return SignalTool().check_connection()
