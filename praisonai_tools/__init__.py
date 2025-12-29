"""PraisonAI Tools - Tools and base classes for AI agents.

This package provides:
1. Base classes for creating custom tools (BaseTool, @tool decorator)
2. Ready-to-use tools for common tasks (Email, Slack, GitHub, etc.)

Usage:
    from praisonai_tools import BaseTool, tool
    
    # Method 1: Using @tool decorator
    @tool
    def my_search(query: str) -> str:
        '''Search for something.'''
        return f"Results for {query}"
    
    # Method 2: Subclassing BaseTool
    class MyTool(BaseTool):
        name = "my_tool"
        description = "Does something useful"
        
        def run(self, query: str) -> str:
            return f"Result for {query}"
    
    # Method 3: Use built-in tools
    from praisonai_tools import EmailTool, SlackTool, GitHubTool
    
    email = EmailTool(provider="gmail")
    slack = SlackTool()
    github = GitHubTool()
    
    # Use with PraisonAI Agents
    from praisonaiagents import Agent
    agent = Agent(tools=[my_search, MyTool(), email, slack])
"""

from importlib.metadata import version, PackageNotFoundError

from praisonai_tools.tools.base import BaseTool, ToolResult, ToolValidationError, validate_tool
from praisonai_tools.tools.decorator import tool, FunctionTool, is_tool, get_tool_schema

try:
    __version__ = version("praisonai-tools")
except PackageNotFoundError:
    __version__ = "0.0.0"
__author__ = "Mervin Praison"

# Lazy imports for tool classes
def __getattr__(name):
    """Lazy load tool classes to avoid loading dependencies until needed."""
    from praisonai_tools.tools import __getattr__ as tools_getattr
    try:
        return tools_getattr(name)
    except AttributeError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Base classes for custom tools
    "BaseTool",
    "ToolResult", 
    "ToolValidationError",
    "validate_tool",
    # Decorator for function-based tools
    "tool",
    "FunctionTool",
    "is_tool",
    "get_tool_schema",
    # Email Tool
    "EmailTool",
    "send_email",
    "read_emails",
    "search_emails",
    # Slack Tool
    "SlackTool",
    "send_slack_message",
    "get_slack_channels",
    "get_slack_history",
    # Discord Tool
    "DiscordTool",
    "send_discord_webhook",
    "send_discord_message",
    # GitHub Tool
    "GitHubTool",
    "search_github_repos",
    "get_github_repo",
    "create_github_issue",
    # Image Tool
    "ImageTool",
    "generate_image",
    # Weather Tool
    "WeatherTool",
    "get_weather",
    "get_forecast",
    "get_air_quality",
    # YouTube Tool
    "YouTubeTool",
    "search_youtube",
    "get_youtube_video",
    "get_youtube_transcript",
    # TTS Tool
    "TTSTool",
    "text_to_speech",
    "list_tts_voices",
    # Telegram Tool
    "TelegramTool",
    "send_telegram_message",
    # Notion Tool
    "NotionTool",
    "search_notion",
    "create_notion_page",
    # PostgreSQL Tool
    "PostgresTool",
    "query_postgres",
    "list_postgres_tables",
    # Reddit Tool
    "RedditTool",
    "search_reddit",
    "get_reddit_hot",
    # Docker Tool
    "DockerTool",
    "list_docker_containers",
    "run_docker_container",
]