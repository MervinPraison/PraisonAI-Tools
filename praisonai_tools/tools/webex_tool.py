"""Webex Tool for PraisonAI Agents.

Manage Webex meetings and messages.

Usage:
    from praisonai_tools import WebexTool
    
    webex = WebexTool()
    rooms = webex.list_rooms()

Environment Variables:
    WEBEX_ACCESS_TOKEN: Webex access token
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class WebexTool(BaseTool):
    """Tool for Webex operations."""
    
    name = "webex"
    description = "Manage Webex meetings and messages."
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("WEBEX_ACCESS_TOKEN")
        super().__init__()
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        if not self.access_token:
            return {"error": "WEBEX_ACCESS_TOKEN required"}
        
        url = f"https://webexapis.com/v1/{endpoint}"
        headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                resp = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "DELETE":
                resp = requests.delete(url, headers=headers, timeout=10)
                if resp.status_code == 204:
                    return {"success": True}
            else:
                return {"error": f"Unknown method: {method}"}
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "list_rooms",
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list_rooms":
            return self.list_rooms()
        elif action == "send_message":
            return self.send_message(**kwargs)
        elif action == "create_meeting":
            return self.create_meeting(**kwargs)
        elif action == "list_meetings":
            return self.list_meetings()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_rooms(self) -> List[Dict[str, Any]]:
        """List rooms."""
        result = self._request("GET", "rooms")
        if "error" in result:
            return [result]
        return result.get("items", [])
    
    def send_message(self, room_id: str = None, person_email: str = None, text: str = None) -> Dict[str, Any]:
        """Send message."""
        if not text:
            return {"error": "text is required"}
        if not room_id and not person_email:
            return {"error": "room_id or person_email is required"}
        
        data = {"text": text}
        if room_id:
            data["roomId"] = room_id
        if person_email:
            data["toPersonEmail"] = person_email
        
        return self._request("POST", "messages", data)
    
    def create_meeting(self, title: str, start: str, end: str) -> Dict[str, Any]:
        """Create meeting."""
        if not title or not start or not end:
            return {"error": "title, start, and end are required"}
        
        data = {"title": title, "start": start, "end": end}
        return self._request("POST", "meetings", data)
    
    def list_meetings(self) -> List[Dict[str, Any]]:
        """List meetings."""
        result = self._request("GET", "meetings")
        if "error" in result:
            return [result]
        return result.get("items", [])


def list_webex_rooms() -> List[Dict[str, Any]]:
    """List Webex rooms."""
    return WebexTool().list_rooms()
