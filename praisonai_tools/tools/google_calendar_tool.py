"""Google Calendar Tool for PraisonAI Agents.

Manage Google Calendar events.

Usage:
    from praisonai_tools import GoogleCalendarTool
    
    calendar = GoogleCalendarTool()
    events = calendar.list_events()

Environment Variables:
    GOOGLE_CALENDAR_CREDENTIALS: Path to credentials.json
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class GoogleCalendarTool(BaseTool):
    """Tool for managing Google Calendar."""
    
    name = "google_calendar"
    description = "Create, list, and manage Google Calendar events."
    
    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
    ):
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "credentials.json")
        self.token_path = token_path or os.getenv("GOOGLE_CALENDAR_TOKEN", "token.json")
        self._service = None
        super().__init__()
    
    @property
    def service(self):
        if self._service is None:
            try:
                from google.oauth2.credentials import Credentials
                from google_auth_oauthlib.flow import InstalledAppFlow
                from google.auth.transport.requests import Request
                from googleapiclient.discovery import build
            except ImportError:
                raise ImportError("google-api-python-client not installed. Install with: pip install google-api-python-client google-auth-oauthlib")
            
            SCOPES = ["https://www.googleapis.com/auth/calendar"]
            creds = None
            
            if os.path.exists(self.token_path):
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        raise ValueError(f"Credentials file not found: {self.credentials_path}")
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                with open(self.token_path, "w") as token:
                    token.write(creds.to_json())
            
            self._service = build("calendar", "v3", credentials=creds)
        return self._service
    
    def run(
        self,
        action: str = "list_events",
        event_id: Optional[str] = None,
        summary: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list_events":
            return self.list_events(**kwargs)
        elif action == "create_event":
            return self.create_event(summary=summary, start=start, end=end, **kwargs)
        elif action == "get_event":
            return self.get_event(event_id=event_id)
        elif action == "delete_event":
            return self.delete_event(event_id=event_id)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_events(self, max_results: int = 10, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """List upcoming events."""
        try:
            now = datetime.utcnow().isoformat() + "Z"
            end_time = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"
            
            events_result = self.service.events().list(
                calendarId="primary",
                timeMin=now,
                timeMax=end_time,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            
            events = []
            for event in events_result.get("items", []):
                start = event["start"].get("dateTime", event["start"].get("date"))
                events.append({
                    "id": event["id"],
                    "summary": event.get("summary", "No title"),
                    "start": start,
                    "end": event["end"].get("dateTime", event["end"].get("date")),
                    "location": event.get("location"),
                })
            return events
        except Exception as e:
            logger.error(f"Google Calendar list_events error: {e}")
            return [{"error": str(e)}]
    
    def create_event(
        self,
        summary: str,
        start: str,
        end: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a calendar event."""
        if not summary:
            return {"error": "summary is required"}
        if not start or not end:
            return {"error": "start and end are required"}
        
        try:
            event = {
                "summary": summary,
                "start": {"dateTime": start, "timeZone": "UTC"},
                "end": {"dateTime": end, "timeZone": "UTC"},
            }
            
            if description:
                event["description"] = description
            if location:
                event["location"] = location
            if attendees:
                event["attendees"] = [{"email": email} for email in attendees]
            
            result = self.service.events().insert(calendarId="primary", body=event).execute()
            
            return {
                "success": True,
                "id": result["id"],
                "summary": result.get("summary"),
                "link": result.get("htmlLink"),
            }
        except Exception as e:
            logger.error(f"Google Calendar create_event error: {e}")
            return {"error": str(e)}
    
    def get_event(self, event_id: str) -> Dict[str, Any]:
        """Get event details."""
        if not event_id:
            return {"error": "event_id is required"}
        
        try:
            event = self.service.events().get(calendarId="primary", eventId=event_id).execute()
            return {
                "id": event["id"],
                "summary": event.get("summary"),
                "start": event["start"].get("dateTime", event["start"].get("date")),
                "end": event["end"].get("dateTime", event["end"].get("date")),
                "description": event.get("description"),
                "location": event.get("location"),
                "attendees": [a.get("email") for a in event.get("attendees", [])],
            }
        except Exception as e:
            logger.error(f"Google Calendar get_event error: {e}")
            return {"error": str(e)}
    
    def delete_event(self, event_id: str) -> Dict[str, Any]:
        """Delete an event."""
        if not event_id:
            return {"error": "event_id is required"}
        
        try:
            self.service.events().delete(calendarId="primary", eventId=event_id).execute()
            return {"success": True, "deleted": event_id}
        except Exception as e:
            logger.error(f"Google Calendar delete_event error: {e}")
            return {"error": str(e)}


def list_calendar_events(max_results: int = 10) -> List[Dict[str, Any]]:
    """List Google Calendar events."""
    return GoogleCalendarTool().list_events(max_results=max_results)
