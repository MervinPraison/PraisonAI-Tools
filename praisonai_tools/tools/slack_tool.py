"""Slack Tool for PraisonAI Agents.

Provides Slack messaging capabilities - send messages, read channels, manage threads.

Usage:
    from praisonai_tools import SlackTool
    
    slack = SlackTool()  # Uses SLACK_TOKEN env var
    
    # Send message
    slack.send_message(channel="#general", text="Hello from AI!")
    
    # List channels
    channels = slack.list_channels()
    
    # Get channel history
    messages = slack.get_history(channel="C01234567", limit=10)

Environment Variables:
    SLACK_TOKEN: Slack Bot User OAuth Token (xoxb-...)
    
Required Slack Bot Scopes:
    - chat:write (send messages)
    - channels:read (list channels)
    - channels:history (read channel history)
    - groups:read (list private channels)
    - groups:history (read private channel history)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SlackTool(BaseTool):
    """Tool for interacting with Slack workspaces.
    
    Send messages, read channel history, list channels, and reply to threads.
    
    Attributes:
        name: Tool identifier
        description: Tool description for LLM
        token: Slack Bot User OAuth Token
        markdown: Enable Slack markdown formatting
    """
    
    name = "slack"
    description = "Send messages to Slack channels, read channel history, list channels, and reply to threads."
    
    def __init__(
        self,
        token: Optional[str] = None,
        markdown: bool = True,
        default_channel: Optional[str] = None,
    ):
        """Initialize SlackTool.
        
        Args:
            token: Slack Bot User OAuth Token (or use SLACK_TOKEN env var)
            markdown: Enable Slack markdown formatting (default: True)
            default_channel: Default channel for messages
        """
        self.token = token or os.getenv("SLACK_TOKEN")
        self.markdown = markdown
        self.default_channel = default_channel
        self._client = None
        
        super().__init__()
    
    @property
    def client(self):
        """Lazy-load Slack client."""
        if self._client is None:
            if not self.token:
                raise ValueError("SLACK_TOKEN not configured. Set SLACK_TOKEN environment variable.")
            try:
                from slack_sdk import WebClient
            except ImportError:
                raise ImportError(
                    "slack_sdk not installed. Install with: pip install slack-sdk"
                )
            self._client = WebClient(token=self.token)
        return self._client
    
    def run(
        self,
        action: str = "send",
        channel: Optional[str] = None,
        text: Optional[str] = None,
        thread_ts: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        """Execute Slack action.
        
        Args:
            action: "send", "list_channels", "history", "reply"
            channel: Channel ID or name (e.g., "#general" or "C01234567")
            text: Message text to send
            thread_ts: Thread timestamp for replies
            limit: Max messages for history
            
        Returns:
            Action result
        """
        action = action.lower()
        channel = channel or self.default_channel
        
        if action == "send":
            return self.send_message(channel=channel, text=text)
        elif action == "reply":
            return self.reply_to_thread(channel=channel, text=text, thread_ts=thread_ts)
        elif action == "list_channels":
            return self.list_channels()
        elif action == "history":
            return self.get_history(channel=channel, limit=limit)
        elif action == "users":
            return self.list_users()
        else:
            return f"Unknown action: {action}. Use 'send', 'reply', 'list_channels', 'history', or 'users'."
    
    def send_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Send a message to a Slack channel.
        
        Args:
            channel: Channel ID or name
            text: Message text
            blocks: Optional Block Kit blocks for rich formatting
            
        Returns:
            API response with message details
        """
        if not channel:
            return {"error": "Channel is required"}
        if not text:
            return {"error": "Text is required"}
        
        try:
            from slack_sdk.errors import SlackApiError
        except ImportError:
            return {"error": "slack_sdk not installed"}
        
        try:
            kwargs = {
                "channel": channel,
                "text": text,
                "mrkdwn": self.markdown,
            }
            if blocks:
                kwargs["blocks"] = blocks
            
            response = self.client.chat_postMessage(**kwargs)
            
            return {
                "success": True,
                "channel": response["channel"],
                "ts": response["ts"],
                "message": response.get("message", {}).get("text", text),
            }
        except SlackApiError as e:
            logger.error(f"Slack API error: {e}")
            return {"error": str(e.response["error"])}
        except Exception as e:
            logger.error(f"Slack error: {e}")
            return {"error": str(e)}
    
    def reply_to_thread(
        self,
        channel: str,
        text: str,
        thread_ts: str,
    ) -> Dict[str, Any]:
        """Reply to a thread in a Slack channel.
        
        Args:
            channel: Channel ID
            text: Reply text
            thread_ts: Parent message timestamp
            
        Returns:
            API response
        """
        if not channel:
            return {"error": "Channel is required"}
        if not text:
            return {"error": "Text is required"}
        if not thread_ts:
            return {"error": "thread_ts is required for replies"}
        
        try:
            from slack_sdk.errors import SlackApiError
        except ImportError:
            return {"error": "slack_sdk not installed"}
        
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts,
                mrkdwn=self.markdown,
            )
            
            return {
                "success": True,
                "channel": response["channel"],
                "ts": response["ts"],
                "thread_ts": thread_ts,
            }
        except SlackApiError as e:
            logger.error(f"Slack API error: {e}")
            return {"error": str(e.response["error"])}
        except Exception as e:
            logger.error(f"Slack error: {e}")
            return {"error": str(e)}
    
    def list_channels(
        self,
        include_private: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List channels in the workspace.
        
        Args:
            include_private: Include private channels
            limit: Max channels to return
            
        Returns:
            List of channel info dicts
        """
        try:
            from slack_sdk.errors import SlackApiError
        except ImportError:
            return [{"error": "slack_sdk not installed"}]
        
        try:
            types = "public_channel,private_channel" if include_private else "public_channel"
            response = self.client.conversations_list(types=types, limit=limit)
            
            channels = []
            for ch in response.get("channels", []):
                channels.append({
                    "id": ch["id"],
                    "name": ch["name"],
                    "is_private": ch.get("is_private", False),
                    "num_members": ch.get("num_members", 0),
                    "topic": ch.get("topic", {}).get("value", ""),
                })
            
            return channels
        except SlackApiError as e:
            logger.error(f"Slack API error: {e}")
            return [{"error": str(e.response["error"])}]
        except Exception as e:
            logger.error(f"Slack error: {e}")
            return [{"error": str(e)}]
    
    def get_history(
        self,
        channel: str,
        limit: int = 10,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get message history from a channel.
        
        Args:
            channel: Channel ID
            limit: Max messages to return
            oldest: Only messages after this timestamp
            latest: Only messages before this timestamp
            
        Returns:
            List of message dicts
        """
        if not channel:
            return [{"error": "Channel is required"}]
        
        try:
            from slack_sdk.errors import SlackApiError
        except ImportError:
            return [{"error": "slack_sdk not installed"}]
        
        try:
            kwargs = {"channel": channel, "limit": limit}
            if oldest:
                kwargs["oldest"] = oldest
            if latest:
                kwargs["latest"] = latest
            
            response = self.client.conversations_history(**kwargs)
            
            messages = []
            for msg in response.get("messages", []):
                messages.append({
                    "text": msg.get("text", ""),
                    "user": msg.get("user", "bot") if msg.get("subtype") != "bot_message" else "bot",
                    "ts": msg.get("ts", ""),
                    "type": msg.get("subtype", "message"),
                    "thread_ts": msg.get("thread_ts"),
                    "reply_count": msg.get("reply_count", 0),
                })
            
            return messages
        except SlackApiError as e:
            logger.error(f"Slack API error: {e}")
            return [{"error": str(e.response["error"])}]
        except Exception as e:
            logger.error(f"Slack error: {e}")
            return [{"error": str(e)}]
    
    def list_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List users in the workspace.
        
        Args:
            limit: Max users to return
            
        Returns:
            List of user info dicts
        """
        try:
            from slack_sdk.errors import SlackApiError
        except ImportError:
            return [{"error": "slack_sdk not installed"}]
        
        try:
            response = self.client.users_list(limit=limit)
            
            users = []
            for user in response.get("members", []):
                if not user.get("deleted") and not user.get("is_bot"):
                    users.append({
                        "id": user["id"],
                        "name": user.get("name", ""),
                        "real_name": user.get("real_name", ""),
                        "email": user.get("profile", {}).get("email", ""),
                    })
            
            return users
        except SlackApiError as e:
            logger.error(f"Slack API error: {e}")
            return [{"error": str(e.response["error"])}]
        except Exception as e:
            logger.error(f"Slack error: {e}")
            return [{"error": str(e)}]


# Convenience functions
def send_slack_message(
    channel: str,
    text: str,
    thread_ts: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a Slack message using environment credentials.
    
    Args:
        channel: Channel ID or name
        text: Message text
        thread_ts: Optional thread to reply to
        
    Returns:
        API response
    """
    tool = SlackTool()
    if thread_ts:
        return tool.reply_to_thread(channel=channel, text=text, thread_ts=thread_ts)
    return tool.send_message(channel=channel, text=text)


def get_slack_channels() -> List[Dict[str, Any]]:
    """List Slack channels using environment credentials."""
    tool = SlackTool()
    return tool.list_channels()


def get_slack_history(channel: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get Slack channel history using environment credentials."""
    tool = SlackTool()
    return tool.get_history(channel=channel, limit=limit)
