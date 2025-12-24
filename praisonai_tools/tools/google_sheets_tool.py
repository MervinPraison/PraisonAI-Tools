"""Google Sheets Tool for PraisonAI Agents.

Read and write Google Sheets.

Usage:
    from praisonai_tools import GoogleSheetsTool
    
    sheets = GoogleSheetsTool()
    data = sheets.read(spreadsheet_id="...", range="Sheet1!A1:D10")

Environment Variables:
    GOOGLE_SHEETS_CREDENTIALS: Path to credentials.json
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class GoogleSheetsTool(BaseTool):
    """Tool for Google Sheets operations."""
    
    name = "google_sheets"
    description = "Read and write Google Sheets data."
    
    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
    ):
        self.credentials_path = credentials_path or os.getenv("GOOGLE_SHEETS_CREDENTIALS", "credentials.json")
        self.token_path = token_path or os.getenv("GOOGLE_SHEETS_TOKEN", "sheets_token.json")
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
                raise ImportError("google-api-python-client not installed")
            
            SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = None
            
            if os.path.exists(self.token_path):
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(self.token_path, "w") as token:
                    token.write(creds.to_json())
            
            self._service = build("sheets", "v4", credentials=creds)
        return self._service
    
    def run(
        self,
        action: str = "read",
        spreadsheet_id: Optional[str] = None,
        range_name: Optional[str] = None,
        values: Optional[List[List]] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[List]]:
        action = action.lower().replace("-", "_")
        
        if action == "read":
            return self.read(spreadsheet_id=spreadsheet_id, range_name=range_name)
        elif action == "write":
            return self.write(spreadsheet_id=spreadsheet_id, range_name=range_name, values=values)
        elif action == "append":
            return self.append(spreadsheet_id=spreadsheet_id, range_name=range_name, values=values)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def read(self, spreadsheet_id: str, range_name: str) -> List[List]:
        """Read data from sheet."""
        if not spreadsheet_id or not range_name:
            return [["error: spreadsheet_id and range_name required"]]
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name,
            ).execute()
            return result.get("values", [])
        except Exception as e:
            logger.error(f"Google Sheets read error: {e}")
            return [[f"error: {e}"]]
    
    def write(self, spreadsheet_id: str, range_name: str, values: List[List]) -> Dict[str, Any]:
        """Write data to sheet."""
        if not spreadsheet_id or not range_name:
            return {"error": "spreadsheet_id and range_name required"}
        if not values:
            return {"error": "values required"}
        
        try:
            body = {"values": values}
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body=body,
            ).execute()
            return {
                "success": True,
                "updated_cells": result.get("updatedCells"),
                "updated_range": result.get("updatedRange"),
            }
        except Exception as e:
            logger.error(f"Google Sheets write error: {e}")
            return {"error": str(e)}
    
    def append(self, spreadsheet_id: str, range_name: str, values: List[List]) -> Dict[str, Any]:
        """Append data to sheet."""
        if not spreadsheet_id or not range_name:
            return {"error": "spreadsheet_id and range_name required"}
        if not values:
            return {"error": "values required"}
        
        try:
            body = {"values": values}
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body=body,
            ).execute()
            return {
                "success": True,
                "updated_cells": result.get("updates", {}).get("updatedCells"),
            }
        except Exception as e:
            logger.error(f"Google Sheets append error: {e}")
            return {"error": str(e)}


def read_google_sheet(spreadsheet_id: str, range_name: str) -> List[List]:
    """Read Google Sheet."""
    return GoogleSheetsTool().read(spreadsheet_id=spreadsheet_id, range_name=range_name)
