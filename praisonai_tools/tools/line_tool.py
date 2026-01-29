"""Line Tool for PraisonAI Agents.

Send messages via LINE Messaging API.

Usage:
    from praisonai_tools import LineTool
    
    line = LineTool()
    line.send_message(to="user_id", message="Hello from AI!")

Environment Variables:
    LINE_CHANNEL_ACCESS_TOKEN: LINE Channel access token
    LINE_CHANNEL_SECRET: LINE Channel secret (for webhook verification)

Setup:
    1. Create a LINE Messaging API channel at https://developers.line.biz/
    2. Get your Channel access token and Channel secret
    3. Set environment variables
"""

import os
import logging
import hashlib
import hmac
import base64
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

# LINE API endpoints
LINE_API_BASE = "https://api.line.me/v2"
LINE_API_DATA = "https://api-data.line.me/v2"


@dataclass
class LineMessageResult:
    """Result of sending a LINE message."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class LineTool(BaseTool):
    """Tool for LINE messaging via Messaging API.
    
    Supports:
    - Push messages to users
    - Reply messages (with reply token)
    - Multicast to multiple users
    - Broadcast to all followers
    - Rich messages (Flex Messages)
    - Quick replies
    
    Based on moltbot's LINE implementation patterns.
    """
    
    name = "line"
    description = "Send messages via LINE Messaging API."
    
    def __init__(
        self,
        channel_access_token: Optional[str] = None,
        channel_secret: Optional[str] = None,
    ):
        """Initialize LineTool.
        
        Args:
            channel_access_token: LINE Channel access token (or use LINE_CHANNEL_ACCESS_TOKEN env var)
            channel_secret: LINE Channel secret (or use LINE_CHANNEL_SECRET env var)
        """
        self.channel_access_token = (
            channel_access_token 
            or os.getenv("LINE_CHANNEL_ACCESS_TOKEN") 
            or os.getenv("LINE_ACCESS_TOKEN")
        )
        self.channel_secret = (
            channel_secret 
            or os.getenv("LINE_CHANNEL_SECRET")
        )
        super().__init__()
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        base_url: str = LINE_API_BASE,
    ) -> Dict[str, Any]:
        """Make LINE API request."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. Install with: pip install requests"}
        
        if not self.channel_access_token:
            return {"error": "LINE_CHANNEL_ACCESS_TOKEN not configured"}
        
        url = f"{base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.channel_access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                if response.text:
                    return response.json()
                return {"success": True}
            
            if response.text:
                error_data = response.json()
                return {"error": error_data.get("message", str(error_data))}
            
            return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"LINE API error: {e}")
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "push",
        to: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """Execute LINE action.
        
        Args:
            action: "push", "reply", "multicast", "broadcast", "get_profile"
            to: User ID, group ID, or room ID
            message: Message text
        """
        action = action.lower().replace("-", "_")
        
        if action == "push":
            return self.push_message(to=to, message=message, **kwargs)
        elif action == "reply":
            return self.reply_message(reply_token=kwargs.get("reply_token"), message=message, **kwargs)
        elif action == "multicast":
            return self.multicast(user_ids=kwargs.get("user_ids", []), message=message, **kwargs)
        elif action == "broadcast":
            return self.broadcast(message=message, **kwargs)
        elif action == "get_profile":
            return self.get_profile(user_id=to)
        elif action == "get_quota":
            return self.get_message_quota()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def _build_text_message(self, text: str) -> Dict[str, Any]:
        """Build a text message object."""
        return {"type": "text", "text": text}
    
    def _build_flex_message(self, alt_text: str, contents: Dict) -> Dict[str, Any]:
        """Build a Flex Message object."""
        return {
            "type": "flex",
            "altText": alt_text,
            "contents": contents,
        }
    
    def _build_image_message(self, original_url: str, preview_url: Optional[str] = None) -> Dict[str, Any]:
        """Build an image message object."""
        return {
            "type": "image",
            "originalContentUrl": original_url,
            "previewImageUrl": preview_url or original_url,
        }
    
    def _build_sticker_message(self, package_id: str, sticker_id: str) -> Dict[str, Any]:
        """Build a sticker message object."""
        return {
            "type": "sticker",
            "packageId": package_id,
            "stickerId": sticker_id,
        }
    
    def push_message(
        self,
        to: str,
        message: str,
        messages: Optional[List[Dict]] = None,
        notification_disabled: bool = False,
    ) -> Dict[str, Any]:
        """Push a message to a user, group, or room.
        
        Args:
            to: User ID, group ID, or room ID
            message: Text message (ignored if messages is provided)
            messages: List of message objects (max 5)
            notification_disabled: Disable push notification
            
        Returns:
            Send result
        """
        if not to:
            return {"error": "Recipient (to) is required"}
        
        # Normalize target ID
        target_id = to.strip()
        if target_id.lower().startswith("line:"):
            target_id = target_id[5:].strip()
        
        if messages:
            msg_list = messages[:5]  # LINE allows max 5 messages
        elif message:
            msg_list = [self._build_text_message(message)]
        else:
            return {"error": "message or messages is required"}
        
        data = {
            "to": target_id,
            "messages": msg_list,
        }
        
        if notification_disabled:
            data["notificationDisabled"] = True
        
        result = self._request("POST", "/bot/message/push", data)
        
        if "error" not in result:
            return {"success": True, "sent_to": target_id}
        return result
    
    def reply_message(
        self,
        reply_token: str,
        message: str,
        messages: Optional[List[Dict]] = None,
        notification_disabled: bool = False,
    ) -> Dict[str, Any]:
        """Reply to a message using a reply token.
        
        Args:
            reply_token: Reply token from webhook event
            message: Text message (ignored if messages is provided)
            messages: List of message objects (max 5)
            notification_disabled: Disable push notification
            
        Returns:
            Send result
        """
        if not reply_token:
            return {"error": "reply_token is required"}
        
        if messages:
            msg_list = messages[:5]
        elif message:
            msg_list = [self._build_text_message(message)]
        else:
            return {"error": "message or messages is required"}
        
        data = {
            "replyToken": reply_token,
            "messages": msg_list,
        }
        
        if notification_disabled:
            data["notificationDisabled"] = True
        
        result = self._request("POST", "/bot/message/reply", data)
        
        if "error" not in result:
            return {"success": True}
        return result
    
    def multicast(
        self,
        user_ids: List[str],
        message: str,
        messages: Optional[List[Dict]] = None,
        notification_disabled: bool = False,
    ) -> Dict[str, Any]:
        """Send message to multiple users.
        
        Args:
            user_ids: List of user IDs (max 500)
            message: Text message (ignored if messages is provided)
            messages: List of message objects (max 5)
            notification_disabled: Disable push notification
            
        Returns:
            Send result
        """
        if not user_ids:
            return {"error": "user_ids is required"}
        
        if messages:
            msg_list = messages[:5]
        elif message:
            msg_list = [self._build_text_message(message)]
        else:
            return {"error": "message or messages is required"}
        
        data = {
            "to": user_ids[:500],  # LINE allows max 500 users
            "messages": msg_list,
        }
        
        if notification_disabled:
            data["notificationDisabled"] = True
        
        result = self._request("POST", "/bot/message/multicast", data)
        
        if "error" not in result:
            return {"success": True, "sent_to_count": len(user_ids[:500])}
        return result
    
    def broadcast(
        self,
        message: str,
        messages: Optional[List[Dict]] = None,
        notification_disabled: bool = False,
    ) -> Dict[str, Any]:
        """Broadcast message to all followers.
        
        Args:
            message: Text message (ignored if messages is provided)
            messages: List of message objects (max 5)
            notification_disabled: Disable push notification
            
        Returns:
            Send result
        """
        if messages:
            msg_list = messages[:5]
        elif message:
            msg_list = [self._build_text_message(message)]
        else:
            return {"error": "message or messages is required"}
        
        data = {"messages": msg_list}
        
        if notification_disabled:
            data["notificationDisabled"] = True
        
        result = self._request("POST", "/bot/message/broadcast", data)
        
        if "error" not in result:
            return {"success": True, "broadcast": True}
        return result
    
    def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile.
        
        Args:
            user_id: LINE user ID
            
        Returns:
            User profile
        """
        if not user_id:
            return {"error": "user_id is required"}
        
        result = self._request("GET", f"/bot/profile/{user_id}")
        
        if "error" not in result:
            return {
                "user_id": result.get("userId"),
                "display_name": result.get("displayName"),
                "picture_url": result.get("pictureUrl"),
                "status_message": result.get("statusMessage"),
            }
        return result
    
    def get_message_quota(self) -> Dict[str, Any]:
        """Get message quota information.
        
        Returns:
            Quota information
        """
        result = self._request("GET", "/bot/message/quota")
        
        if "error" not in result:
            return {
                "type": result.get("type"),
                "value": result.get("value"),
            }
        return result
    
    def send_flex_message(
        self,
        to: str,
        alt_text: str,
        contents: Dict,
    ) -> Dict[str, Any]:
        """Send a Flex Message.
        
        Args:
            to: User ID, group ID, or room ID
            alt_text: Alternative text for notifications
            contents: Flex Message contents (bubble or carousel)
            
        Returns:
            Send result
        """
        flex_msg = self._build_flex_message(alt_text, contents)
        return self.push_message(to=to, message="", messages=[flex_msg])
    
    def send_image(
        self,
        to: str,
        image_url: str,
        preview_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an image message.
        
        Args:
            to: User ID, group ID, or room ID
            image_url: URL of the image
            preview_url: URL of the preview image
            
        Returns:
            Send result
        """
        img_msg = self._build_image_message(image_url, preview_url)
        return self.push_message(to=to, message="", messages=[img_msg])
    
    def verify_signature(self, body: bytes, signature: str) -> bool:
        """Verify webhook signature.
        
        Args:
            body: Request body bytes
            signature: X-Line-Signature header value
            
        Returns:
            True if signature is valid
        """
        if not self.channel_secret:
            logger.warning("LINE_CHANNEL_SECRET not configured, skipping signature verification")
            return True
        
        hash_value = hmac.new(
            self.channel_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).digest()
        expected_signature = base64.b64encode(hash_value).decode("utf-8")
        
        return hmac.compare_digest(signature, expected_signature)


def send_line_message(to: str, message: str) -> Dict[str, Any]:
    """Send a LINE message.
    
    Args:
        to: User ID, group ID, or room ID
        message: Message text
        
    Returns:
        Send result
    """
    return LineTool().push_message(to=to, message=message)


def broadcast_line_message(message: str) -> Dict[str, Any]:
    """Broadcast a LINE message to all followers.
    
    Args:
        message: Message text
        
    Returns:
        Send result
    """
    return LineTool().broadcast(message=message)
