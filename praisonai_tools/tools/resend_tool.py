"""Resend Tool for PraisonAI Agents.

Send emails via Resend API.

Usage:
    from praisonai_tools import ResendTool
    
    resend = ResendTool()
    resend.send_email(to="user@example.com", subject="Hello", body="Hi!")

Environment Variables:
    RESEND_API_KEY: Resend API key
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ResendTool(BaseTool):
    """Tool for Resend email."""
    
    name = "resend"
    description = "Send emails via Resend API."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("RESEND_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "send",
        to: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "send":
            return self.send_email(to=to, subject=subject, body=body, **kwargs)
        return {"error": f"Unknown action: {action}"}
    
    def send_email(self, to: str, subject: str, body: str, from_email: str = None) -> Dict[str, Any]:
        """Send email."""
        if not to or not subject or not body:
            return {"error": "to, subject, and body are required"}
        if not self.api_key:
            return {"error": "RESEND_API_KEY required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {
                "from": from_email or "onboarding@resend.dev",
                "to": [to],
                "subject": subject,
                "text": body,
            }
            resp = requests.post("https://api.resend.com/emails", headers=headers, json=data, timeout=10)
            result = resp.json()
            
            if "id" in result:
                return {"success": True, "id": result["id"]}
            return {"error": result.get("message", str(result))}
        except Exception as e:
            logger.error(f"Resend send_email error: {e}")
            return {"error": str(e)}


def resend_send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Send email via Resend."""
    return ResendTool().send_email(to=to, subject=subject, body=body)
