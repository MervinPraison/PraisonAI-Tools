"""Gmail Tool for PraisonAI Agents.

Send and read emails via Gmail API.

Usage:
    from praisonai_tools import GmailTool
    
    gmail = GmailTool()
    emails = gmail.list_emails()

Environment Variables:
    GMAIL_CREDENTIALS_FILE: Path to credentials.json
    GMAIL_TOKEN_FILE: Path to token.json
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class GmailTool(BaseTool):
    """Tool for Gmail operations."""
    
    name = "gmail"
    description = "Send and read emails via Gmail API."
    
    def __init__(
        self,
        credentials_file: Optional[str] = None,
        token_file: Optional[str] = None,
    ):
        self.credentials_file = credentials_file or os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
        self.token_file = token_file or os.getenv("GMAIL_TOKEN_FILE", "token.json")
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
                raise ImportError("google-api-python-client, google-auth-oauthlib required")
            
            SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
            creds = None
            
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(self.token_file, "w") as token:
                    token.write(creds.to_json())
            
            self._service = build("gmail", "v1", credentials=creds)
        return self._service
    
    def run(
        self,
        action: str = "list",
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list":
            return self.list_emails(**kwargs)
        elif action == "get":
            return self.get_email(message_id=kwargs.get("message_id"))
        elif action == "send":
            return self.send_email(**kwargs)
        elif action == "search":
            return self.search_emails(query=kwargs.get("query"), **kwargs)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_emails(self, max_results: int = 10, label: str = "INBOX") -> List[Dict[str, Any]]:
        """List emails."""
        try:
            results = self.service.users().messages().list(
                userId="me", labelIds=[label], maxResults=max_results
            ).execute()
            
            messages = results.get("messages", [])
            emails = []
            for msg in messages:
                email_data = self.service.users().messages().get(
                    userId="me", id=msg["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]
                ).execute()
                
                headers = {h["name"]: h["value"] for h in email_data.get("payload", {}).get("headers", [])}
                emails.append({
                    "id": msg["id"],
                    "from": headers.get("From", ""),
                    "subject": headers.get("Subject", ""),
                    "date": headers.get("Date", ""),
                    "snippet": email_data.get("snippet", ""),
                })
            return emails
        except Exception as e:
            logger.error(f"Gmail list error: {e}")
            return [{"error": str(e)}]
    
    def get_email(self, message_id: str) -> Dict[str, Any]:
        """Get email by ID."""
        if not message_id:
            return {"error": "message_id is required"}
        
        try:
            email_data = self.service.users().messages().get(
                userId="me", id=message_id, format="full"
            ).execute()
            
            headers = {h["name"]: h["value"] for h in email_data.get("payload", {}).get("headers", [])}
            
            body = ""
            payload = email_data.get("payload", {})
            if "body" in payload and payload["body"].get("data"):
                import base64
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
            elif "parts" in payload:
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                        import base64
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                        break
            
            return {
                "id": message_id,
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "body": body,
            }
        except Exception as e:
            logger.error(f"Gmail get error: {e}")
            return {"error": str(e)}
    
    def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Send email."""
        if not to or not subject:
            return {"error": "to and subject are required"}
        
        try:
            import base64
            from email.mime.text import MIMEText
            
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            result = self.service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()
            
            return {"success": True, "id": result.get("id")}
        except Exception as e:
            logger.error(f"Gmail send error: {e}")
            return {"error": str(e)}
    
    def search_emails(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search emails."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            results = self.service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()
            
            messages = results.get("messages", [])
            emails = []
            for msg in messages:
                email_data = self.service.users().messages().get(
                    userId="me", id=msg["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]
                ).execute()
                
                headers = {h["name"]: h["value"] for h in email_data.get("payload", {}).get("headers", [])}
                emails.append({
                    "id": msg["id"],
                    "from": headers.get("From", ""),
                    "subject": headers.get("Subject", ""),
                    "date": headers.get("Date", ""),
                })
            return emails
        except Exception as e:
            logger.error(f"Gmail search error: {e}")
            return [{"error": str(e)}]


def list_gmail_emails(max_results: int = 10) -> List[Dict[str, Any]]:
    """List Gmail emails."""
    return GmailTool().list_emails(max_results=max_results)
