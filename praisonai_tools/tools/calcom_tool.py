"""Cal.com Tool for PraisonAI Agents.

Manage Cal.com scheduling.

Usage:
    from praisonai_tools import CalComTool
    
    cal = CalComTool()
    bookings = cal.list_bookings()

Environment Variables:
    CALCOM_API_KEY: Cal.com API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class CalComTool(BaseTool):
    """Tool for Cal.com scheduling."""
    
    name = "calcom"
    description = "Manage Cal.com scheduling and bookings."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CALCOM_API_KEY")
        super().__init__()
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        if not self.api_key:
            return {"error": "CALCOM_API_KEY required"}
        
        url = f"https://api.cal.com/v1/{endpoint}?apiKey={self.api_key}"
        
        try:
            if method == "GET":
                resp = requests.get(url, timeout=10)
            elif method == "POST":
                resp = requests.post(url, json=data, timeout=10)
            else:
                return {"error": f"Unknown method: {method}"}
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "list_bookings",
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list_bookings":
            return self.list_bookings()
        elif action == "list_event_types":
            return self.list_event_types()
        elif action == "get_availability":
            return self.get_availability(**kwargs)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_bookings(self) -> List[Dict[str, Any]]:
        """List bookings."""
        result = self._request("GET", "bookings")
        if "error" in result:
            return [result]
        return result.get("bookings", [])
    
    def list_event_types(self) -> List[Dict[str, Any]]:
        """List event types."""
        result = self._request("GET", "event-types")
        if "error" in result:
            return [result]
        return result.get("event_types", [])
    
    def get_availability(self, username: str, date_from: str, date_to: str) -> Dict[str, Any]:
        """Get availability."""
        if not username or not date_from or not date_to:
            return {"error": "username, date_from, and date_to are required"}
        return self._request("GET", f"availability?username={username}&dateFrom={date_from}&dateTo={date_to}")


def calcom_list_bookings() -> List[Dict[str, Any]]:
    """List Cal.com bookings."""
    return CalComTool().list_bookings()
