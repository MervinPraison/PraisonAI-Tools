"""iMessage Tool for PraisonAI Agents.

Send messages via iMessage on macOS using AppleScript or imessage-rest API.

Usage:
    from praisonai_tools import iMessageTool
    
    imsg = iMessageTool()
    imsg.send_message(to="+1234567890", message="Hello from AI!")

Environment Variables:
    IMESSAGE_API_URL: imessage-rest API URL (optional, for REST mode)
    IMESSAGE_MODE: "applescript" (default) or "rest"

Requirements:
    - macOS only (for AppleScript mode)
    - Messages.app must be configured
    - Full Disk Access may be required for some operations
"""

import os
import logging
import subprocess
import platform
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


@dataclass
class iMessageSendResult:
    """Result of sending an iMessage."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class iMessageTool(BaseTool):
    """Tool for iMessage on macOS.
    
    Supports two modes:
    1. AppleScript mode (default): Direct integration with Messages.app
    2. REST mode: Uses imessage-rest API server
    
    Based on moltbot's iMessage implementation patterns.
    """
    
    name = "imessage"
    description = "Send messages via iMessage on macOS."
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        mode: Optional[str] = None,
    ):
        """Initialize iMessageTool.
        
        Args:
            api_url: imessage-rest API URL (for REST mode)
            mode: "applescript" or "rest"
        """
        self.api_url = api_url or os.getenv("IMESSAGE_API_URL")
        self.mode = mode or os.getenv("IMESSAGE_MODE", "applescript")
        self._is_macos = platform.system() == "Darwin"
        super().__init__()
    
    def _check_macos(self) -> Optional[Dict[str, Any]]:
        """Check if running on macOS."""
        if not self._is_macos:
            return {"error": "iMessage is only available on macOS"}
        return None
    
    def _run_applescript(self, script: str) -> Dict[str, Any]:
        """Run AppleScript and return result."""
        check = self._check_macos()
        if check:
            return check
        
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "AppleScript execution failed"
                return {"error": error_msg}
            
            return {"success": True, "output": result.stdout.strip()}
        except subprocess.TimeoutExpired:
            return {"error": "AppleScript execution timed out"}
        except Exception as e:
            logger.error(f"AppleScript error: {e}")
            return {"error": str(e)}
    
    def _rest_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make REST API request."""
        if not self.api_url:
            return {"error": "IMESSAGE_API_URL not configured for REST mode"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. Install with: pip install requests"}
        
        url = f"{self.api_url.rstrip('/')}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(url, json=data, timeout=10)
            
            if response.status_code in (200, 201):
                if response.text:
                    return response.json()
                return {"success": True}
            
            return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"iMessage REST API error: {e}")
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "send",
        to: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """Execute iMessage action.
        
        Args:
            action: "send", "check", "list_chats"
            to: Recipient phone number, email, or chat ID
            message: Message text
        """
        action = action.lower().replace("-", "_")
        
        if action == "send":
            return self.send_message(to=to, message=message, **kwargs)
        elif action == "check":
            return self.check_availability()
        elif action == "list_chats":
            return self.list_chats(**kwargs)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def _normalize_recipient(self, to: str) -> str:
        """Normalize recipient identifier."""
        value = to.strip()
        
        # Remove imessage: or imsg: prefix
        lower = value.lower()
        if lower.startswith("imessage:"):
            value = value[9:].strip()
        elif lower.startswith("imsg:"):
            value = value[5:].strip()
        
        return value
    
    def _escape_applescript_string(self, text: str) -> str:
        """Escape string for AppleScript."""
        return text.replace("\\", "\\\\").replace('"', '\\"')
    
    def send_message(
        self,
        to: str,
        message: str,
        service: str = "iMessage",
    ) -> Dict[str, Any]:
        """Send an iMessage.
        
        Args:
            to: Recipient phone number or email
            message: Message text
            service: "iMessage" or "SMS"
            
        Returns:
            Send result
        """
        if not to:
            return {"error": "Recipient (to) is required"}
        if not message:
            return {"error": "Message is required"}
        
        recipient = self._normalize_recipient(to)
        
        if self.mode == "rest" and self.api_url:
            return self._send_via_rest(recipient, message)
        else:
            return self._send_via_applescript(recipient, message, service)
    
    def _send_via_applescript(
        self,
        to: str,
        message: str,
        service: str = "iMessage",
    ) -> Dict[str, Any]:
        """Send message via AppleScript."""
        escaped_to = self._escape_applescript_string(to)
        escaped_message = self._escape_applescript_string(message)
        
        # AppleScript to send iMessage
        script = f'''
tell application "Messages"
    set targetService to 1st service whose service type = {service}
    set targetBuddy to buddy "{escaped_to}" of targetService
    send "{escaped_message}" to targetBuddy
end tell
'''
        
        result = self._run_applescript(script)
        
        if "error" in result:
            # Try alternative approach for phone numbers
            if "@" not in to:
                alt_script = f'''
tell application "Messages"
    set targetBuddy to buddy "{escaped_to}" of (service 1 whose service type is iMessage)
    send "{escaped_message}" to targetBuddy
end tell
'''
                result = self._run_applescript(alt_script)
        
        if "error" not in result:
            return {"success": True, "sent_to": to}
        return result
    
    def _send_via_rest(self, to: str, message: str) -> Dict[str, Any]:
        """Send message via REST API."""
        data = {
            "recipient": to,
            "message": message,
        }
        
        result = self._rest_request("POST", "/send", data)
        
        if "error" not in result:
            return {
                "success": True,
                "sent_to": to,
                "message_id": result.get("message_id"),
            }
        return result
    
    def check_availability(self) -> Dict[str, Any]:
        """Check if iMessage is available.
        
        Returns:
            Availability status
        """
        if self.mode == "rest" and self.api_url:
            result = self._rest_request("GET", "/status")
            if "error" not in result:
                return {"available": True, "mode": "rest"}
            return {"available": False, "error": result.get("error")}
        
        check = self._check_macos()
        if check:
            return {"available": False, "error": check.get("error")}
        
        # Check if Messages.app is available
        script = '''
tell application "System Events"
    return exists application process "Messages"
end tell
'''
        result = self._run_applescript(script)
        
        if "error" not in result:
            return {"available": True, "mode": "applescript", "macos": True}
        return {"available": False, "error": result.get("error")}
    
    def list_chats(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent chats.
        
        Args:
            limit: Maximum number of chats to return
            
        Returns:
            List of chats
        """
        if self.mode == "rest" and self.api_url:
            result = self._rest_request("GET", f"/chats?limit={limit}")
            if "error" not in result:
                return result.get("chats", [])
            return [result]
        
        check = self._check_macos()
        if check:
            return [check]
        
        # AppleScript to list chats
        script = f'''
tell application "Messages"
    set chatList to {{}}
    set chatCount to 0
    repeat with aChat in chats
        if chatCount < {limit} then
            set chatInfo to name of aChat
            set end of chatList to chatInfo
            set chatCount to chatCount + 1
        end if
    end repeat
    return chatList
end tell
'''
        
        result = self._run_applescript(script)
        
        if "error" not in result:
            output = result.get("output", "")
            if output:
                chats = [c.strip() for c in output.split(",") if c.strip()]
                return [{"name": chat} for chat in chats]
            return []
        return [result]
    
    def send_to_group(
        self,
        group_name: str,
        message: str,
    ) -> Dict[str, Any]:
        """Send message to a group chat.
        
        Args:
            group_name: Name of the group chat
            message: Message text
            
        Returns:
            Send result
        """
        if not group_name:
            return {"error": "group_name is required"}
        if not message:
            return {"error": "message is required"}
        
        if self.mode == "rest" and self.api_url:
            data = {
                "group": group_name,
                "message": message,
            }
            return self._rest_request("POST", "/send/group", data)
        
        escaped_group = self._escape_applescript_string(group_name)
        escaped_message = self._escape_applescript_string(message)
        
        script = f'''
tell application "Messages"
    set targetChat to chat "{escaped_group}"
    send "{escaped_message}" to targetChat
end tell
'''
        
        result = self._run_applescript(script)
        
        if "error" not in result:
            return {"success": True, "sent_to_group": group_name}
        return result


def send_imessage(to: str, message: str) -> Dict[str, Any]:
    """Send an iMessage.
    
    Args:
        to: Recipient phone number or email
        message: Message text
        
    Returns:
        Send result
    """
    return iMessageTool().send_message(to=to, message=message)


def check_imessage_availability() -> Dict[str, Any]:
    """Check if iMessage is available."""
    return iMessageTool().check_availability()
