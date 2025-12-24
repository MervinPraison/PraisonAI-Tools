"""Twilio Tool for PraisonAI Agents.

Send SMS and make calls using Twilio.

Usage:
    from praisonai_tools import TwilioTool
    
    twilio = TwilioTool()
    twilio.send_sms(to="+1234567890", body="Hello!")

Environment Variables:
    TWILIO_ACCOUNT_SID: Twilio Account SID
    TWILIO_AUTH_TOKEN: Twilio Auth Token
    TWILIO_PHONE_NUMBER: Default from phone number
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class TwilioTool(BaseTool):
    """Tool for Twilio SMS and calls."""
    
    name = "twilio"
    description = "Send SMS messages and make calls using Twilio."
    
    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
    ):
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = from_number or os.getenv("TWILIO_PHONE_NUMBER")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                from twilio.rest import Client
            except ImportError:
                raise ImportError("twilio not installed. Install with: pip install twilio")
            
            if not self.account_sid or not self.auth_token:
                raise ValueError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN required")
            
            self._client = Client(self.account_sid, self.auth_token)
        return self._client
    
    def run(
        self,
        action: str = "send_sms",
        to: Optional[str] = None,
        body: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        action = action.lower().replace("-", "_")
        
        if action == "send_sms":
            return self.send_sms(to=to, body=body)
        elif action == "send_whatsapp":
            return self.send_whatsapp(to=to, body=body)
        elif action == "make_call":
            return self.make_call(to=to, **kwargs)
        elif action == "get_messages":
            return self.get_messages(**kwargs)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def send_sms(self, to: str, body: str, from_number: Optional[str] = None) -> Dict[str, Any]:
        """Send SMS message."""
        if not to or not body:
            return {"error": "to and body are required"}
        
        try:
            message = self.client.messages.create(
                body=body,
                from_=from_number or self.from_number,
                to=to,
            )
            return {
                "success": True,
                "sid": message.sid,
                "status": message.status,
                "to": to,
            }
        except Exception as e:
            logger.error(f"Twilio send_sms error: {e}")
            return {"error": str(e)}
    
    def send_whatsapp(self, to: str, body: str) -> Dict[str, Any]:
        """Send WhatsApp message."""
        if not to or not body:
            return {"error": "to and body are required"}
        
        try:
            message = self.client.messages.create(
                body=body,
                from_=f"whatsapp:{self.from_number}",
                to=f"whatsapp:{to}",
            )
            return {
                "success": True,
                "sid": message.sid,
                "status": message.status,
            }
        except Exception as e:
            logger.error(f"Twilio send_whatsapp error: {e}")
            return {"error": str(e)}
    
    def make_call(self, to: str, twiml: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
        """Make a phone call."""
        if not to:
            return {"error": "to is required"}
        if not twiml and not url:
            return {"error": "twiml or url is required"}
        
        try:
            params = {
                "to": to,
                "from_": self.from_number,
            }
            if twiml:
                params["twiml"] = twiml
            if url:
                params["url"] = url
            
            call = self.client.calls.create(**params)
            return {
                "success": True,
                "sid": call.sid,
                "status": call.status,
            }
        except Exception as e:
            logger.error(f"Twilio make_call error: {e}")
            return {"error": str(e)}
    
    def get_messages(self, limit: int = 20) -> list:
        """Get recent messages."""
        try:
            messages = self.client.messages.list(limit=limit)
            return [
                {
                    "sid": m.sid,
                    "from": m.from_,
                    "to": m.to,
                    "body": m.body,
                    "status": m.status,
                    "date_sent": str(m.date_sent),
                }
                for m in messages
            ]
        except Exception as e:
            logger.error(f"Twilio get_messages error: {e}")
            return [{"error": str(e)}]


def send_sms(to: str, body: str) -> Dict[str, Any]:
    """Send SMS via Twilio."""
    return TwilioTool().send_sms(to=to, body=body)
