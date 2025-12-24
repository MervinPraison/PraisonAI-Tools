"""Zoom Tool for PraisonAI Agents.

Manage Zoom meetings.

Usage:
    from praisonai_tools import ZoomTool
    
    zoom = ZoomTool()
    meetings = zoom.list_meetings()

Environment Variables:
    ZOOM_ACCOUNT_ID: Zoom account ID
    ZOOM_CLIENT_ID: Zoom client ID
    ZOOM_CLIENT_SECRET: Zoom client secret
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ZoomTool(BaseTool):
    """Tool for Zoom meetings."""
    
    name = "zoom"
    description = "Manage Zoom meetings."
    
    def __init__(
        self,
        account_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.account_id = account_id or os.getenv("ZOOM_ACCOUNT_ID")
        self.client_id = client_id or os.getenv("ZOOM_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("ZOOM_CLIENT_SECRET")
        self._token = None
        super().__init__()
    
    def _get_token(self) -> str:
        if self._token:
            return self._token
        
        import requests
        import base64
        
        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        resp = requests.post(
            "https://zoom.us/oauth/token",
            headers={"Authorization": f"Basic {credentials}"},
            data={"grant_type": "account_credentials", "account_id": self.account_id},
            timeout=10,
        )
        self._token = resp.json().get("access_token")
        return self._token
    
    def run(
        self,
        action: str = "list",
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list":
            return self.list_meetings()
        elif action == "create":
            return self.create_meeting(**kwargs)
        elif action == "get":
            return self.get_meeting(meeting_id=kwargs.get("meeting_id"))
        elif action == "delete":
            return self.delete_meeting(meeting_id=kwargs.get("meeting_id"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_meetings(self) -> List[Dict[str, Any]]:
        """List meetings."""
        if not all([self.account_id, self.client_id, self.client_secret]):
            return [{"error": "ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET required"}]
        
        try:
            import requests
        except ImportError:
            return [{"error": "requests not installed"}]
        
        try:
            token = self._get_token()
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get("https://api.zoom.us/v2/users/me/meetings", headers=headers, timeout=10)
            data = resp.json()
            
            meetings = []
            for m in data.get("meetings", []):
                meetings.append({
                    "id": m.get("id"),
                    "topic": m.get("topic"),
                    "start_time": m.get("start_time"),
                    "duration": m.get("duration"),
                    "join_url": m.get("join_url"),
                })
            return meetings
        except Exception as e:
            logger.error(f"Zoom list error: {e}")
            return [{"error": str(e)}]
    
    def create_meeting(self, topic: str, duration: int = 60, start_time: str = None) -> Dict[str, Any]:
        """Create meeting."""
        if not topic:
            return {"error": "topic is required"}
        if not all([self.account_id, self.client_id, self.client_secret]):
            return {"error": "Zoom credentials required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            token = self._get_token()
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            data = {"topic": topic, "type": 2, "duration": duration}
            if start_time:
                data["start_time"] = start_time
            
            resp = requests.post(
                "https://api.zoom.us/v2/users/me/meetings",
                headers=headers,
                json=data,
                timeout=10,
            )
            result = resp.json()
            
            return {
                "id": result.get("id"),
                "topic": result.get("topic"),
                "join_url": result.get("join_url"),
                "start_url": result.get("start_url"),
            }
        except Exception as e:
            logger.error(f"Zoom create error: {e}")
            return {"error": str(e)}
    
    def get_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """Get meeting details."""
        if not meeting_id:
            return {"error": "meeting_id is required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            token = self._get_token()
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"https://api.zoom.us/v2/meetings/{meeting_id}", headers=headers, timeout=10)
            return resp.json()
        except Exception as e:
            logger.error(f"Zoom get error: {e}")
            return {"error": str(e)}
    
    def delete_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """Delete meeting."""
        if not meeting_id:
            return {"error": "meeting_id is required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            token = self._get_token()
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.delete(f"https://api.zoom.us/v2/meetings/{meeting_id}", headers=headers, timeout=10)
            if resp.status_code == 204:
                return {"success": True}
            return resp.json()
        except Exception as e:
            logger.error(f"Zoom delete error: {e}")
            return {"error": str(e)}


def list_zoom_meetings() -> List[Dict[str, Any]]:
    """List Zoom meetings."""
    return ZoomTool().list_meetings()
