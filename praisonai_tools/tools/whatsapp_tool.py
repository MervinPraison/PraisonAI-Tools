"""WhatsApp Tool for PraisonAI Agents.

Send messages via WhatsApp Business API.

Usage:
    from praisonai_tools import WhatsAppTool
    
    wa = WhatsAppTool()
    wa.send_message(to="+1234567890", message="Hello!")

Environment Variables:
    WHATSAPP_ACCESS_TOKEN: WhatsApp Business API access token
    WHATSAPP_PHONE_NUMBER_ID: Phone number ID
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class WhatsAppTool(BaseTool):
    """Tool for WhatsApp messaging."""
    
    name = "whatsapp"
    description = "Send messages via WhatsApp Business API."
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
    ):
        self.access_token = access_token or os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = phone_number_id or os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        super().__init__()
    
    def run(
        self,
        action: str = "send",
        to: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        action = action.lower().replace("-", "_")
        
        if action == "send":
            return self.send_message(to=to, message=message)
        elif action == "send_template":
            return self.send_template(to=to, template=kwargs.get("template"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def send_message(self, to: str, message: str) -> Dict[str, Any]:
        """Send text message."""
        if not to or not message:
            return {"error": "to and message are required"}
        if not self.access_token or not self.phone_number_id:
            return {"error": "WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
            data = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message},
            }
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            result = resp.json()
            
            if "error" in result:
                return {"error": result["error"].get("message", str(result["error"]))}
            return {"success": True, "message_id": result.get("messages", [{}])[0].get("id")}
        except Exception as e:
            logger.error(f"WhatsApp send error: {e}")
            return {"error": str(e)}
    
    def send_template(self, to: str, template: str, language: str = "en_US") -> Dict[str, Any]:
        """Send template message."""
        if not to or not template:
            return {"error": "to and template are required"}
        if not self.access_token or not self.phone_number_id:
            return {"error": "WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID required"}
        
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        try:
            url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
            data = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {"name": template, "language": {"code": language}},
            }
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            result = resp.json()
            
            if "error" in result:
                return {"error": result["error"].get("message", str(result["error"]))}
            return {"success": True, "message_id": result.get("messages", [{}])[0].get("id")}
        except Exception as e:
            logger.error(f"WhatsApp template error: {e}")
            return {"error": str(e)}


def send_whatsapp_message(to: str, message: str) -> Dict[str, Any]:
    """Send WhatsApp message."""
    return WhatsAppTool().send_message(to=to, message=message)
