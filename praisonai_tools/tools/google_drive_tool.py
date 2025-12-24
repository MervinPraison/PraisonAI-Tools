"""Google Drive Tool for PraisonAI Agents.

Google Drive file operations.

Usage:
    from praisonai_tools import GoogleDriveTool
    
    drive = GoogleDriveTool()
    files = drive.list_files()

Environment Variables:
    GOOGLE_DRIVE_CREDENTIALS_FILE: Path to credentials.json
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class GoogleDriveTool(BaseTool):
    """Tool for Google Drive operations."""
    
    name = "google_drive"
    description = "Google Drive file operations."
    
    def __init__(self, credentials_file: Optional[str] = None):
        self.credentials_file = credentials_file or os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE", "credentials.json")
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
                raise ImportError("google-api-python-client required")
            
            SCOPES = ["https://www.googleapis.com/auth/drive"]
            creds = None
            token_file = "drive_token.json"
            
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(token_file, "w") as token:
                    token.write(creds.to_json())
            
            self._service = build("drive", "v3", credentials=creds)
        return self._service
    
    def run(
        self,
        action: str = "list",
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list":
            return self.list_files(**kwargs)
        elif action == "get":
            return self.get_file(file_id=kwargs.get("file_id"))
        elif action == "search":
            return self.search(query=kwargs.get("query"))
        elif action == "download":
            return self.download(file_id=kwargs.get("file_id"), output_path=kwargs.get("output_path"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_files(self, page_size: int = 20) -> List[Dict[str, Any]]:
        """List files."""
        try:
            results = self.service.files().list(
                pageSize=page_size,
                fields="files(id, name, mimeType, modifiedTime)"
            ).execute()
            return results.get("files", [])
        except Exception as e:
            logger.error(f"Google Drive list error: {e}")
            return [{"error": str(e)}]
    
    def get_file(self, file_id: str) -> Dict[str, Any]:
        """Get file metadata."""
        if not file_id:
            return {"error": "file_id is required"}
        try:
            return self.service.files().get(fileId=file_id).execute()
        except Exception as e:
            logger.error(f"Google Drive get error: {e}")
            return {"error": str(e)}
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search files."""
        if not query:
            return [{"error": "query is required"}]
        try:
            results = self.service.files().list(
                q=f"name contains '{query}'",
                fields="files(id, name, mimeType)"
            ).execute()
            return results.get("files", [])
        except Exception as e:
            logger.error(f"Google Drive search error: {e}")
            return [{"error": str(e)}]
    
    def download(self, file_id: str, output_path: str) -> Dict[str, Any]:
        """Download file."""
        if not file_id or not output_path:
            return {"error": "file_id and output_path are required"}
        try:
            from googleapiclient.http import MediaIoBaseDownload
            import io
            
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            with open(output_path, "wb") as f:
                f.write(fh.getvalue())
            return {"success": True, "output_path": output_path}
        except Exception as e:
            logger.error(f"Google Drive download error: {e}")
            return {"error": str(e)}


def list_drive_files(page_size: int = 20) -> List[Dict[str, Any]]:
    """List Google Drive files."""
    return GoogleDriveTool().list_files(page_size=page_size)
