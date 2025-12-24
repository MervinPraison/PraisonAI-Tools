"""Telegram Tool for PraisonAI Agents.

Send messages to Telegram chats and channels via Bot API.

Usage:
    from praisonai_tools import TelegramTool
    
    telegram = TelegramTool(chat_id="123456789")  # Uses TELEGRAM_BOT_TOKEN env var
    telegram.send_message("Hello from AI!")

Environment Variables:
    TELEGRAM_BOT_TOKEN: Telegram Bot API token (get from @BotFather)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class TelegramTool(BaseTool):
    """Tool for sending messages to Telegram."""
    
    name = "telegram"
    description = "Send messages to Telegram chats and channels."
    
    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[Union[str, int]] = None,
    ):
        """Initialize TelegramTool.
        
        Args:
            token: Telegram Bot API token (or use TELEGRAM_BOT_TOKEN env var)
            chat_id: Default chat ID to send messages to
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
        self.chat_id = chat_id
        self.api_base = "https://api.telegram.org"
        super().__init__()
    
    def _request(self, method: str, data: Dict) -> Dict:
        """Make Telegram API request."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. Install with: pip install requests"}
        
        if not self.token:
            return {"error": "TELEGRAM_BOT_TOKEN not configured"}
        
        try:
            url = f"{self.api_base}/bot{self.token}/{method}"
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if not result.get("ok"):
                return {"error": result.get("description", "Unknown error")}
            
            return result
        except Exception as e:
            logger.error(f"Telegram API error: {e}")
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "send_message",
        text: Optional[str] = None,
        chat_id: Optional[Union[str, int]] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """Execute Telegram action.
        
        Args:
            action: "send_message", "send_photo", "get_me", "get_updates"
            text: Message text
            chat_id: Target chat ID (overrides default)
        """
        action = action.lower().replace("-", "_")
        target_chat = chat_id or self.chat_id
        
        if action == "send_message":
            return self.send_message(text=text, chat_id=target_chat, **kwargs)
        elif action == "send_photo":
            return self.send_photo(chat_id=target_chat, **kwargs)
        elif action == "get_me":
            return self.get_me()
        elif action == "get_updates":
            return self.get_updates(**kwargs)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def send_message(
        self,
        text: str,
        chat_id: Optional[Union[str, int]] = None,
        parse_mode: Optional[str] = None,
        disable_notification: bool = False,
        reply_to_message_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Send a text message.
        
        Args:
            text: Message text
            chat_id: Target chat ID
            parse_mode: "HTML", "Markdown", or "MarkdownV2"
            disable_notification: Send silently
            reply_to_message_id: Reply to specific message
            
        Returns:
            Message result
        """
        target_chat = chat_id or self.chat_id
        if not target_chat:
            return {"error": "chat_id is required"}
        
        if not text:
            return {"error": "text is required"}
        
        data = {
            "chat_id": target_chat,
            "text": text,
        }
        
        if parse_mode:
            data["parse_mode"] = parse_mode
        if disable_notification:
            data["disable_notification"] = True
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        
        result = self._request("sendMessage", data)
        
        if "error" not in result:
            msg = result.get("result", {})
            return {
                "success": True,
                "message_id": msg.get("message_id"),
                "chat_id": msg.get("chat", {}).get("id"),
                "text": msg.get("text"),
            }
        return result
    
    def send_photo(
        self,
        photo: str,
        chat_id: Optional[Union[str, int]] = None,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a photo.
        
        Args:
            photo: Photo URL or file_id
            chat_id: Target chat ID
            caption: Photo caption
            
        Returns:
            Message result
        """
        target_chat = chat_id or self.chat_id
        if not target_chat:
            return {"error": "chat_id is required"}
        
        if not photo:
            return {"error": "photo is required"}
        
        data = {
            "chat_id": target_chat,
            "photo": photo,
        }
        
        if caption:
            data["caption"] = caption
        
        result = self._request("sendPhoto", data)
        
        if "error" not in result:
            return {"success": True, "message_id": result.get("result", {}).get("message_id")}
        return result
    
    def get_me(self) -> Dict[str, Any]:
        """Get bot information.
        
        Returns:
            Bot info
        """
        result = self._request("getMe", {})
        
        if "error" not in result:
            bot = result.get("result", {})
            return {
                "id": bot.get("id"),
                "username": bot.get("username"),
                "first_name": bot.get("first_name"),
                "can_join_groups": bot.get("can_join_groups"),
            }
        return result
    
    def get_updates(self, limit: int = 10, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent updates/messages.
        
        Args:
            limit: Max updates to return
            offset: Update offset
            
        Returns:
            List of updates
        """
        data = {"limit": limit}
        if offset:
            data["offset"] = offset
        
        result = self._request("getUpdates", data)
        
        if "error" not in result:
            updates = result.get("result", [])
            return [
                {
                    "update_id": u.get("update_id"),
                    "message": u.get("message", {}).get("text"),
                    "chat_id": u.get("message", {}).get("chat", {}).get("id"),
                    "from": u.get("message", {}).get("from", {}).get("username"),
                }
                for u in updates
            ]
        return [result]


def send_telegram_message(text: str, chat_id: Union[str, int]) -> Dict[str, Any]:
    """Send a Telegram message."""
    return TelegramTool().send_message(text=text, chat_id=chat_id)
