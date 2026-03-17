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
        
        actions = {
            "list": lambda: self.list_emails(**kwargs),
            "get": lambda: self.get_email(message_id=kwargs.get("message_id")),
            "send": lambda: self.send_email(**kwargs),
            "search": lambda: self.search_emails(query=kwargs.get("query"), **kwargs),
            "archive": lambda: self.archive_email(message_id=kwargs.get("message_id")),
            "label": lambda: self.label_email(
                message_id=kwargs.get("message_id"), label=kwargs.get("label")
            ),
            "mark_read": lambda: self.mark_read(message_id=kwargs.get("message_id")),
            "draft": lambda: self.draft_email(**kwargs),
            "trash": lambda: self.trash_email(message_id=kwargs.get("message_id")),
        }
        
        handler = actions.get(action)
        if handler:
            return handler()
        return {"error": f"Unknown action: {action}. Available: {', '.join(actions)}"}
    
    def _get_message_headers(self, message_id: str) -> Dict[str, Any]:
        """Get message metadata headers."""
        email_data = self.service.users().messages().get(
            userId="me", id=message_id, format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in email_data.get("payload", {}).get("headers", [])}
        return {
            "id": message_id,
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": email_data.get("snippet", ""),
        }
    
    def list_emails(self, max_results: int = 10, label: str = "INBOX") -> List[Dict[str, Any]]:
        """List emails."""
        try:
            results = self.service.users().messages().list(
                userId="me", labelIds=[label], maxResults=max_results
            ).execute()
            messages = results.get("messages", [])
            return [self._get_message_headers(msg["id"]) for msg in messages]
        except Exception as e:
            logger.error(f"Gmail list error: {e}")
            return [{"error": str(e)}]
    
    def get_email(self, message_id: str) -> Dict[str, Any]:
        """Get full email by ID."""
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
        """Search emails using Gmail query syntax (e.g. from:, subject:, is:unread)."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            results = self.service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()
            messages = results.get("messages", [])
            return [self._get_message_headers(msg["id"]) for msg in messages]
        except Exception as e:
            logger.error(f"Gmail search error: {e}")
            return [{"error": str(e)}]
    
    def archive_email(self, message_id: str) -> Dict[str, Any]:
        """Archive an email (remove from Inbox, keep in All Mail)."""
        if not message_id:
            return {"error": "message_id is required"}
        
        try:
            self.service.users().messages().modify(
                userId="me", id=message_id,
                body={"removeLabelIds": ["INBOX"]}
            ).execute()
            logger.info(f"Gmail archived: {message_id}")
            return {"success": True, "id": message_id, "action": "archived"}
        except Exception as e:
            logger.error(f"Gmail archive error: {e}")
            return {"error": str(e)}
    
    def label_email(self, message_id: str, label: str) -> Dict[str, Any]:
        """Add a label to an email. Creates the label if it doesn't exist."""
        if not message_id or not label:
            return {"error": "message_id and label are required"}
        
        try:
            # Resolve label name to ID (create if missing)
            label_id = self._resolve_label_id(label)
            
            self.service.users().messages().modify(
                userId="me", id=message_id,
                body={"addLabelIds": [label_id]}
            ).execute()
            logger.info(f"Gmail labeled {message_id} with {label}")
            return {"success": True, "id": message_id, "label": label, "label_id": label_id}
        except Exception as e:
            logger.error(f"Gmail label error: {e}")
            return {"error": str(e)}
    
    def _resolve_label_id(self, label_name: str) -> str:
        """Find label ID by name, create if it doesn't exist."""
        # Check system labels first
        system_labels = {
            "INBOX": "INBOX", "SENT": "SENT", "TRASH": "TRASH",
            "SPAM": "SPAM", "DRAFT": "DRAFT", "STARRED": "STARRED",
            "IMPORTANT": "IMPORTANT", "UNREAD": "UNREAD",
        }
        if label_name.upper() in system_labels:
            return system_labels[label_name.upper()]
        
        # Search user labels
        results = self.service.users().labels().list(userId="me").execute()
        for lbl in results.get("labels", []):
            if lbl["name"].lower() == label_name.lower():
                return lbl["id"]
        
        # Create new label
        new_label = self.service.users().labels().create(
            userId="me", body={"name": label_name}
        ).execute()
        return new_label["id"]
    
    def mark_read(self, message_id: str) -> Dict[str, Any]:
        """Mark an email as read (remove UNREAD label)."""
        if not message_id:
            return {"error": "message_id is required"}
        
        try:
            self.service.users().messages().modify(
                userId="me", id=message_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            logger.info(f"Gmail marked read: {message_id}")
            return {"success": True, "id": message_id, "action": "marked_read"}
        except Exception as e:
            logger.error(f"Gmail mark_read error: {e}")
            return {"error": str(e)}
    
    def draft_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Create an email draft (doesn't send it)."""
        if not to or not subject:
            return {"error": "to and subject are required"}
        
        try:
            import base64
            from email.mime.text import MIMEText
            
            message = MIMEText(body or "")
            message["to"] = to
            message["subject"] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            result = self.service.users().drafts().create(
                userId="me", body={"message": {"raw": raw}}
            ).execute()
            
            draft_id = result.get("id", "unknown")
            logger.info(f"Gmail draft created: {draft_id}")
            return {"success": True, "draft_id": draft_id, "action": "draft_created"}
        except Exception as e:
            logger.error(f"Gmail draft error: {e}")
            return {"error": str(e)}
    
    def trash_email(self, message_id: str) -> Dict[str, Any]:
        """Move an email to trash."""
        if not message_id:
            return {"error": "message_id is required"}
        
        try:
            self.service.users().messages().trash(
                userId="me", id=message_id
            ).execute()
            logger.info(f"Gmail trashed: {message_id}")
            return {"success": True, "id": message_id, "action": "trashed"}
        except Exception as e:
            logger.error(f"Gmail trash error: {e}")
            return {"error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience functions for direct use
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def list_gmail_emails(max_results: int = 10) -> List[Dict[str, Any]]:
    """List Gmail emails."""
    return GmailTool().list_emails(max_results=max_results)


def gmail_archive_email(message_id: str) -> Dict[str, Any]:
    """Archive a Gmail email (remove from Inbox).

    Args:
        message_id: Gmail message ID (get from list_gmail_emails)

    Returns:
        Success or error dict
    """
    return GmailTool().archive_email(message_id)


def gmail_label_email(message_id: str, label: str) -> Dict[str, Any]:
    """Add a label to a Gmail email. Creates the label if needed.

    Args:
        message_id: Gmail message ID
        label: Label name (e.g. "Newsletters", "Important")

    Returns:
        Success or error dict
    """
    return GmailTool().label_email(message_id, label)


def gmail_mark_read(message_id: str) -> Dict[str, Any]:
    """Mark a Gmail email as read.

    Args:
        message_id: Gmail message ID

    Returns:
        Success or error dict
    """
    return GmailTool().mark_read(message_id)


def gmail_draft_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Create a Gmail draft (doesn't send).

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body text

    Returns:
        Dict with draft_id
    """
    return GmailTool().draft_email(to, subject, body)


def gmail_trash_email(message_id: str) -> Dict[str, Any]:
    """Move a Gmail email to trash.

    Args:
        message_id: Gmail message ID

    Returns:
        Success or error dict
    """
    return GmailTool().trash_email(message_id)
