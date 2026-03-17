"""Outlook Tool for PraisonAI Agents.

Send, read, search, archive, and draft emails via Microsoft Graph API.

Usage:
    from praisonai_tools import OutlookTool

    outlook = OutlookTool()
    emails = outlook.list_emails()

Environment Variables:
    OUTLOOK_CLIENT_ID: Azure AD app client ID
    OUTLOOK_CLIENT_SECRET: Azure AD app client secret
    OUTLOOK_TENANT_ID: Azure AD tenant ID (default: "common")
    OUTLOOK_TOKEN_FILE: Path to cached token (default: outlook_token.json)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class OutlookTool(BaseTool):
    """Tool for Outlook/Microsoft 365 email operations via Graph API."""

    name = "outlook"
    description = "Send, read, search, archive, and draft emails via Microsoft Graph API."

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    SCOPES = ["https://graph.microsoft.com/Mail.ReadWrite", "https://graph.microsoft.com/Mail.Send"]

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None,
        token_file: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("OUTLOOK_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("OUTLOOK_CLIENT_SECRET", "")
        self.tenant_id = tenant_id or os.getenv("OUTLOOK_TENANT_ID", "common")
        self.token_file = token_file or os.getenv("OUTLOOK_TOKEN_FILE", "outlook_token.json")
        self._token = None
        super().__init__()

    @property
    def token(self) -> str:
        """Get a valid access token, refreshing if needed."""
        if self._token:
            return self._token

        if not self.client_id:
            raise ValueError(
                "OUTLOOK_CLIENT_ID is required. "
                "Register an app at https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps"
            )

        try:
            from msal import PublicClientApplication, SerializableTokenCache
        except ImportError:
            raise ImportError("msal package required. Install with: pip install msal")

        cache = SerializableTokenCache()
        if os.path.exists(self.token_file):
            with open(self.token_file, "r") as f:
                cache.deserialize(f.read())

        app = PublicClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            token_cache=cache,
        )

        # Try cached token first
        accounts = app.get_accounts()
        result = None
        if accounts:
            result = app.acquire_token_silent(self.SCOPES, account=accounts[0])

        if not result:
            # Interactive sign-in
            result = app.acquire_token_interactive(scopes=self.SCOPES)

        if "access_token" in result:
            self._token = result["access_token"]
            # Cache the token
            if cache.has_state_changed:
                with open(self.token_file, "w") as f:
                    f.write(cache.serialize())
            return self._token

        raise ValueError(f"Failed to acquire token: {result.get('error_description', result)}")

    def _graph_request(self, method: str, endpoint: str, json_body: dict = None) -> dict:
        """Make a Microsoft Graph API request."""
        try:
            import requests
        except ImportError:
            raise ImportError("requests package required. Install with: pip install requests")

        url = f"{self.GRAPH_BASE}{endpoint}"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

        response = requests.request(method, url, headers=headers, json=json_body)

        if response.status_code == 204:
            return {"success": True}
        if response.ok:
            return response.json()
        return {"error": f"Graph API error {response.status_code}: {response.text}"}

    def run(self, action: str = "list", **kwargs) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        actions = {
            "list": lambda: self.list_emails(**kwargs),
            "get": lambda: self.read_email(message_id=kwargs.get("message_id")),
            "send": lambda: self.send_email(**kwargs),
            "search": lambda: self.search_emails(query=kwargs.get("query"), **kwargs),
            "archive": lambda: self.archive_email(message_id=kwargs.get("message_id")),
            "draft": lambda: self.draft_email(**kwargs),
            "mark_read": lambda: self.mark_read(message_id=kwargs.get("message_id")),
            "trash": lambda: self.trash_email(message_id=kwargs.get("message_id")),
        }
        handler = actions.get(action)
        if handler:
            return handler()
        return {"error": f"Unknown action: {action}. Available: {', '.join(actions)}"}

    def list_emails(self, limit: int = 10, folder: str = "inbox") -> List[Dict[str, Any]]:
        """List recent emails."""
        try:
            data = self._graph_request("GET", f"/me/mailFolders/{folder}/messages?$top={limit}&$orderby=receivedDateTime desc")
            if "error" in data:
                return [data]
            messages = data.get("value", [])
            return [
                {
                    "id": msg["id"],
                    "from": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
                    "subject": msg.get("subject", "(no subject)"),
                    "date": msg.get("receivedDateTime", ""),
                    "snippet": msg.get("bodyPreview", "")[:100],
                    "is_read": msg.get("isRead", False),
                }
                for msg in messages
            ]
        except Exception as e:
            logger.error(f"Outlook list error: {e}")
            return [{"error": str(e)}]

    def read_email(self, message_id: str) -> Dict[str, Any]:
        """Read full email by ID."""
        if not message_id:
            return {"error": "message_id is required"}
        try:
            data = self._graph_request("GET", f"/me/messages/{message_id}")
            if "error" in data:
                return data
            return {
                "id": message_id,
                "from": data.get("from", {}).get("emailAddress", {}).get("address", ""),
                "to": ", ".join(
                    r.get("emailAddress", {}).get("address", "")
                    for r in data.get("toRecipients", [])
                ),
                "subject": data.get("subject", ""),
                "date": data.get("receivedDateTime", ""),
                "body": data.get("body", {}).get("content", ""),
            }
        except Exception as e:
            logger.error(f"Outlook read error: {e}")
            return {"error": str(e)}

    def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Send an email."""
        if not to or not subject:
            return {"error": "to and subject are required"}
        try:
            payload = {
                "message": {
                    "subject": subject,
                    "body": {"contentType": "Text", "content": body or ""},
                    "toRecipients": [{"emailAddress": {"address": to}}],
                },
                "saveToSentItems": True,
            }
            result = self._graph_request("POST", "/me/sendMail", payload)
            if "error" in result:
                return result
            logger.info(f"Outlook email sent to {to}")
            return {"success": True, "to": to}
        except Exception as e:
            logger.error(f"Outlook send error: {e}")
            return {"error": str(e)}

    def search_emails(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search emails using OData $search query."""
        if not query:
            return [{"error": "query is required"}]
        try:
            data = self._graph_request(
                "GET", f'/me/messages?$search="{query}"&$top={limit}&$orderby=receivedDateTime desc'
            )
            if "error" in data:
                return [data]
            messages = data.get("value", [])
            return [
                {
                    "id": msg["id"],
                    "from": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
                    "subject": msg.get("subject", "(no subject)"),
                    "date": msg.get("receivedDateTime", ""),
                }
                for msg in messages
            ]
        except Exception as e:
            logger.error(f"Outlook search error: {e}")
            return [{"error": str(e)}]

    def archive_email(self, message_id: str) -> Dict[str, Any]:
        """Archive an email (move to Archive folder)."""
        if not message_id:
            return {"error": "message_id is required"}
        try:
            # Get Archive folder ID
            folders = self._graph_request("GET", "/me/mailFolders?$filter=displayName eq 'Archive'")
            if "error" in folders:
                return folders
            folder_list = folders.get("value", [])
            if not folder_list:
                return {"error": "Archive folder not found"}
            archive_id = folder_list[0]["id"]
            result = self._graph_request("POST", f"/me/messages/{message_id}/move", {"destinationId": archive_id})
            if "error" in result:
                return result
            logger.info(f"Outlook archived: {message_id}")
            return {"success": True, "id": message_id, "action": "archived"}
        except Exception as e:
            logger.error(f"Outlook archive error: {e}")
            return {"error": str(e)}

    def draft_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Create an email draft (doesn't send it)."""
        if not to or not subject:
            return {"error": "to and subject are required"}
        try:
            payload = {
                "subject": subject,
                "body": {"contentType": "Text", "content": body or ""},
                "toRecipients": [{"emailAddress": {"address": to}}],
            }
            result = self._graph_request("POST", "/me/messages", payload)
            if "error" in result:
                return result
            draft_id = result.get("id", "unknown")
            logger.info(f"Outlook draft created: {draft_id}")
            return {"success": True, "draft_id": draft_id, "action": "draft_created"}
        except Exception as e:
            logger.error(f"Outlook draft error: {e}")
            return {"error": str(e)}

    def mark_read(self, message_id: str) -> Dict[str, Any]:
        """Mark an email as read."""
        if not message_id:
            return {"error": "message_id is required"}
        try:
            result = self._graph_request("PATCH", f"/me/messages/{message_id}", {"isRead": True})
            if "error" in result:
                return result
            logger.info(f"Outlook marked read: {message_id}")
            return {"success": True, "id": message_id, "action": "marked_read"}
        except Exception as e:
            logger.error(f"Outlook mark_read error: {e}")
            return {"error": str(e)}

    def trash_email(self, message_id: str) -> Dict[str, Any]:
        """Move an email to trash (Deleted Items)."""
        if not message_id:
            return {"error": "message_id is required"}
        try:
            result = self._graph_request("POST", f"/me/messages/{message_id}/move", {"destinationId": "deleteditems"})
            if "error" in result:
                return result
            logger.info(f"Outlook trashed: {message_id}")
            return {"success": True, "id": message_id, "action": "trashed"}
        except Exception as e:
            logger.error(f"Outlook trash error: {e}")
            return {"error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience functions for direct use
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def outlook_list_emails(limit: int = 10) -> List[Dict[str, Any]]:
    """List Outlook emails.

    Args:
        limit: Max emails to return

    Returns:
        List of email dicts
    """
    return OutlookTool().list_emails(limit=limit)


def outlook_send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Send an Outlook email.

    Args:
        to: Recipient email
        subject: Email subject
        body: Email body

    Returns:
        Success or error dict
    """
    return OutlookTool().send_email(to, subject, body)


def outlook_search_emails(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search Outlook emails.

    Args:
        query: Search text
        limit: Max results

    Returns:
        List of matching email dicts
    """
    return OutlookTool().search_emails(query, limit)


def outlook_archive_email(message_id: str) -> Dict[str, Any]:
    """Archive an Outlook email.

    Args:
        message_id: Outlook message ID

    Returns:
        Success or error dict
    """
    return OutlookTool().archive_email(message_id)


def outlook_draft_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Create an Outlook draft email.

    Args:
        to: Recipient
        subject: Subject
        body: Body text

    Returns:
        Dict with draft_id
    """
    return OutlookTool().draft_email(to, subject, body)
