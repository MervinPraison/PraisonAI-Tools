"""Discord Tool for PraisonAI Agents.

Send messages and interact with Discord servers via webhooks or bot.

Usage:
    from praisonai_tools import DiscordTool
    
    # Using webhook (simplest)
    discord = DiscordTool(webhook_url="https://discord.com/api/webhooks/...")
    discord.send_webhook("Hello from AI!")
    
    # Using bot token
    discord = DiscordTool()  # Uses DISCORD_BOT_TOKEN env var
    discord.send_message(channel_id="123456789", content="Hello!")

Environment Variables:
    DISCORD_BOT_TOKEN: Discord bot token
    DISCORD_WEBHOOK_URL: Default webhook URL
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class DiscordTool(BaseTool):
    """Tool for interacting with Discord."""
    
    name = "discord"
    description = "Send messages to Discord channels via webhooks or bot."
    
    def __init__(
        self,
        bot_token: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ):
        """Initialize DiscordTool.
        
        Args:
            bot_token: Discord bot token (or use DISCORD_BOT_TOKEN env var)
            webhook_url: Discord webhook URL (or use DISCORD_WEBHOOK_URL env var)
        """
        self.bot_token = bot_token or os.getenv("DISCORD_BOT_TOKEN")
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        self.api_base = "https://discord.com/api/v10"
        super().__init__()
    
    def _request(self, method: str, url: str, json_data: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict:
        """Make HTTP request."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. Install with: pip install requests"}
        
        try:
            hdrs = headers or {}
            if self.bot_token and "Authorization" not in hdrs:
                hdrs["Authorization"] = f"Bot {self.bot_token}"
            hdrs["Content-Type"] = "application/json"
            
            response = requests.request(method, url, json=json_data, headers=hdrs, timeout=10)
            
            if response.status_code == 204:
                return {"success": True}
            
            if response.ok:
                return response.json() if response.text else {"success": True}
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Discord API error: {e}")
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "send_webhook",
        content: Optional[str] = None,
        channel_id: Optional[str] = None,
        webhook_url: Optional[str] = None,
        username: Optional[str] = None,
        embed: Optional[Dict] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """Execute Discord action.
        
        Args:
            action: "send_webhook", "send_message", "get_channel"
            content: Message content
            channel_id: Discord channel ID
            webhook_url: Override webhook URL
            username: Override webhook username
            embed: Embed object for rich messages
        """
        action = action.lower().replace("-", "_")
        
        if action == "send_webhook":
            return self.send_webhook(content=content, webhook_url=webhook_url, username=username, embed=embed)
        elif action == "send_message":
            return self.send_message(channel_id=channel_id, content=content, embed=embed)
        elif action == "get_channel":
            return self.get_channel(channel_id=channel_id)
        elif action == "list_guilds":
            return self.list_guilds()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def send_webhook(
        self,
        content: str,
        webhook_url: Optional[str] = None,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        embed: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Send message via Discord webhook.
        
        Args:
            content: Message text
            webhook_url: Webhook URL (uses default if not provided)
            username: Override bot username
            avatar_url: Override bot avatar
            embed: Rich embed object
            
        Returns:
            Success status
        """
        url = webhook_url or self.webhook_url
        if not url:
            return {"error": "Webhook URL required. Set DISCORD_WEBHOOK_URL or provide webhook_url."}
        
        if not content and not embed:
            return {"error": "Content or embed required"}
        
        payload = {}
        if content:
            payload["content"] = content
        if username:
            payload["username"] = username
        if avatar_url:
            payload["avatar_url"] = avatar_url
        if embed:
            payload["embeds"] = [embed]
        
        result = self._request("POST", url, json_data=payload, headers={})
        
        if "error" not in result:
            return {"success": True, "message": "Webhook message sent"}
        return result
    
    def send_message(
        self,
        channel_id: str,
        content: str,
        embed: Optional[Dict] = None,
        reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send message to a Discord channel (requires bot token).
        
        Args:
            channel_id: Discord channel ID
            content: Message text
            embed: Rich embed object
            reply_to: Message ID to reply to
            
        Returns:
            Message data
        """
        if not self.bot_token:
            return {"error": "Bot token required. Set DISCORD_BOT_TOKEN."}
        
        if not channel_id:
            return {"error": "Channel ID required"}
        
        if not content and not embed:
            return {"error": "Content or embed required"}
        
        url = f"{self.api_base}/channels/{channel_id}/messages"
        
        payload = {}
        if content:
            payload["content"] = content
        if embed:
            payload["embeds"] = [embed]
        if reply_to:
            payload["message_reference"] = {"message_id": reply_to}
        
        result = self._request("POST", url, json_data=payload)
        
        if "error" not in result:
            return {
                "success": True,
                "message_id": result.get("id"),
                "channel_id": result.get("channel_id"),
                "content": result.get("content"),
            }
        return result
    
    def get_channel(self, channel_id: str) -> Dict[str, Any]:
        """Get channel information.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Channel data
        """
        if not self.bot_token:
            return {"error": "Bot token required"}
        
        if not channel_id:
            return {"error": "Channel ID required"}
        
        url = f"{self.api_base}/channels/{channel_id}"
        result = self._request("GET", url)
        
        if "error" not in result:
            return {
                "id": result.get("id"),
                "name": result.get("name"),
                "type": result.get("type"),
                "guild_id": result.get("guild_id"),
                "topic": result.get("topic"),
            }
        return result
    
    def list_guilds(self) -> List[Dict[str, Any]]:
        """List guilds (servers) the bot is in.
        
        Returns:
            List of guild data
        """
        if not self.bot_token:
            return [{"error": "Bot token required"}]
        
        url = f"{self.api_base}/users/@me/guilds"
        result = self._request("GET", url)
        
        if isinstance(result, list):
            return [{"id": g.get("id"), "name": g.get("name"), "icon": g.get("icon")} for g in result]
        return [result]
    
    def get_messages(
        self,
        channel_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get recent messages from a channel.
        
        Args:
            channel_id: Discord channel ID
            limit: Max messages to return
            
        Returns:
            List of messages
        """
        if not self.bot_token:
            return [{"error": "Bot token required"}]
        
        if not channel_id:
            return [{"error": "Channel ID required"}]
        
        url = f"{self.api_base}/channels/{channel_id}/messages?limit={limit}"
        result = self._request("GET", url)
        
        if isinstance(result, list):
            return [
                {
                    "id": m.get("id"),
                    "content": m.get("content"),
                    "author": m.get("author", {}).get("username"),
                    "timestamp": m.get("timestamp"),
                }
                for m in result
            ]
        return [result]
    
    @staticmethod
    def create_embed(
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: int = 0x5865F2,
        url: Optional[str] = None,
        fields: Optional[List[Dict]] = None,
        footer: Optional[str] = None,
        image_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
    ) -> Dict:
        """Create a Discord embed object.
        
        Args:
            title: Embed title
            description: Embed description
            color: Embed color (hex)
            url: Title URL
            fields: List of {"name": str, "value": str, "inline": bool}
            footer: Footer text
            image_url: Main image URL
            thumbnail_url: Thumbnail URL
            
        Returns:
            Embed dict for use with send methods
        """
        embed = {"color": color}
        if title:
            embed["title"] = title
        if description:
            embed["description"] = description
        if url:
            embed["url"] = url
        if fields:
            embed["fields"] = fields
        if footer:
            embed["footer"] = {"text": footer}
        if image_url:
            embed["image"] = {"url": image_url}
        if thumbnail_url:
            embed["thumbnail"] = {"url": thumbnail_url}
        return embed


def send_discord_webhook(content: str, webhook_url: Optional[str] = None, username: Optional[str] = None) -> Dict[str, Any]:
    """Send a Discord webhook message."""
    return DiscordTool(webhook_url=webhook_url).send_webhook(content=content, username=username)


def send_discord_message(channel_id: str, content: str) -> Dict[str, Any]:
    """Send a Discord message via bot."""
    return DiscordTool().send_message(channel_id=channel_id, content=content)
