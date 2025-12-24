"""Tests for PraisonAI Tools."""

import pytest


class TestEmailTool:
    """Tests for EmailTool."""
    
    def test_import(self):
        from praisonai_tools import EmailTool
        assert EmailTool is not None
    
    def test_instantiation(self):
        from praisonai_tools import EmailTool
        tool = EmailTool(provider="gmail")
        assert tool.name == "email"
        assert tool.smtp_host == "smtp.gmail.com"
        assert tool.smtp_port == 587
    
    def test_provider_config(self):
        from praisonai_tools import EmailTool
        
        # Gmail
        gmail = EmailTool(provider="gmail")
        assert gmail.smtp_host == "smtp.gmail.com"
        
        # Outlook
        outlook = EmailTool(provider="outlook")
        assert outlook.smtp_host == "smtp.office365.com"
        
        # Yahoo
        yahoo = EmailTool(provider="yahoo")
        assert yahoo.smtp_host == "smtp.mail.yahoo.com"
    
    def test_schema_generation(self):
        from praisonai_tools import EmailTool
        tool = EmailTool()
        schema = tool.get_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "email"
    
    def test_send_without_credentials(self):
        from praisonai_tools import EmailTool
        tool = EmailTool(username=None, password=None)
        result = tool.send(to="test@example.com", subject="Test", body="Test body")
        assert "Error" in result or "error" in result.lower()


class TestSlackTool:
    """Tests for SlackTool."""
    
    def test_import(self):
        from praisonai_tools import SlackTool
        assert SlackTool is not None
    
    def test_instantiation(self):
        from praisonai_tools import SlackTool
        tool = SlackTool()
        assert tool.name == "slack"
    
    def test_schema_generation(self):
        from praisonai_tools import SlackTool
        tool = SlackTool()
        schema = tool.get_schema()
        assert schema["function"]["name"] == "slack"
    
    def test_send_without_token(self):
        from praisonai_tools import SlackTool
        tool = SlackTool(token=None)
        # Should raise error when trying to use client
        with pytest.raises(ValueError):
            _ = tool.client


class TestDiscordTool:
    """Tests for DiscordTool."""
    
    def test_import(self):
        from praisonai_tools import DiscordTool
        assert DiscordTool is not None
    
    def test_instantiation(self):
        from praisonai_tools import DiscordTool
        tool = DiscordTool()
        assert tool.name == "discord"
    
    def test_webhook_without_url(self):
        from praisonai_tools import DiscordTool
        tool = DiscordTool(webhook_url=None)
        result = tool.send_webhook(content="Test")
        assert "error" in result
    
    def test_create_embed(self):
        from praisonai_tools import DiscordTool
        embed = DiscordTool.create_embed(
            title="Test",
            description="Test description",
            color=0xFF0000
        )
        assert embed["title"] == "Test"
        assert embed["description"] == "Test description"
        assert embed["color"] == 0xFF0000


class TestGitHubTool:
    """Tests for GitHubTool."""
    
    def test_import(self):
        from praisonai_tools import GitHubTool
        assert GitHubTool is not None
    
    def test_instantiation(self):
        from praisonai_tools import GitHubTool
        tool = GitHubTool()
        assert tool.name == "github"
    
    def test_schema_generation(self):
        from praisonai_tools import GitHubTool
        tool = GitHubTool()
        schema = tool.get_schema()
        assert schema["function"]["name"] == "github"
    
    def test_search_without_query(self):
        from praisonai_tools import GitHubTool
        tool = GitHubTool()
        result = tool.search_repos(query=None)
        assert result[0].get("error") is not None


class TestImageTool:
    """Tests for ImageTool."""
    
    def test_import(self):
        from praisonai_tools import ImageTool
        assert ImageTool is not None
    
    def test_instantiation(self):
        from praisonai_tools import ImageTool
        tool = ImageTool(model="dall-e-3")
        assert tool.name == "image_generate"
        assert tool.model == "dall-e-3"
    
    def test_invalid_model(self):
        from praisonai_tools import ImageTool
        with pytest.raises(ValueError):
            ImageTool(model="invalid-model")
    
    def test_invalid_size_dalle3(self):
        from praisonai_tools import ImageTool
        with pytest.raises(ValueError):
            ImageTool(model="dall-e-3", size="256x256")
    
    def test_schema_generation(self):
        from praisonai_tools import ImageTool
        tool = ImageTool()
        schema = tool.get_schema()
        assert schema["function"]["name"] == "image_generate"


class TestWeatherTool:
    """Tests for WeatherTool."""
    
    def test_import(self):
        from praisonai_tools import WeatherTool
        assert WeatherTool is not None
    
    def test_instantiation(self):
        from praisonai_tools import WeatherTool
        tool = WeatherTool(units="metric")
        assert tool.name == "weather"
        assert tool.units == "metric"
    
    def test_units_config(self):
        from praisonai_tools import WeatherTool
        
        metric = WeatherTool(units="metric")
        assert metric.units == "metric"
        
        imperial = WeatherTool(units="imperial")
        assert imperial.units == "imperial"
    
    def test_without_api_key(self):
        from praisonai_tools import WeatherTool
        tool = WeatherTool(api_key=None)
        result = tool.get_current(location="London")
        assert "error" in result


class TestYouTubeTool:
    """Tests for YouTubeTool."""
    
    def test_import(self):
        from praisonai_tools import YouTubeTool
        assert YouTubeTool is not None
    
    def test_instantiation(self):
        from praisonai_tools import YouTubeTool
        tool = YouTubeTool()
        assert tool.name == "youtube"
    
    def test_extract_video_id(self):
        from praisonai_tools import YouTubeTool
        
        # Direct ID
        assert YouTubeTool._extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
        
        # Full URL
        assert YouTubeTool._extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
        
        # Short URL
        assert YouTubeTool._extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    
    def test_search_without_query(self):
        from praisonai_tools import YouTubeTool
        tool = YouTubeTool()
        result = tool.search(query=None)
        assert result[0].get("error") is not None


class TestTTSTool:
    """Tests for TTSTool."""
    
    def test_import(self):
        from praisonai_tools import TTSTool
        assert TTSTool is not None
    
    def test_instantiation(self):
        from praisonai_tools import TTSTool
        tool = TTSTool(provider="openai")
        assert tool.name == "text_to_speech"
        assert tool.provider == "openai"
    
    def test_list_openai_voices(self):
        from praisonai_tools import TTSTool
        tool = TTSTool(provider="openai")
        result = tool.list_voices()
        assert result["provider"] == "openai"
        assert "alloy" in result["voices"]
    
    def test_speak_requires_text(self):
        from praisonai_tools import TTSTool
        tool = TTSTool()
        result = tool.speak(text="")
        assert "error" in result


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_send_email_import(self):
        from praisonai_tools import send_email
        assert callable(send_email)
    
    def test_send_slack_message_import(self):
        from praisonai_tools import send_slack_message
        assert callable(send_slack_message)
    
    def test_send_discord_webhook_import(self):
        from praisonai_tools import send_discord_webhook
        assert callable(send_discord_webhook)
    
    def test_search_github_repos_import(self):
        from praisonai_tools import search_github_repos
        assert callable(search_github_repos)
    
    def test_generate_image_import(self):
        from praisonai_tools import generate_image
        assert callable(generate_image)
    
    def test_get_weather_import(self):
        from praisonai_tools import get_weather
        assert callable(get_weather)
    
    def test_search_youtube_import(self):
        from praisonai_tools import search_youtube
        assert callable(search_youtube)
    
    def test_text_to_speech_import(self):
        from praisonai_tools import text_to_speech
        assert callable(text_to_speech)


class TestTelegramTool:
    """Tests for TelegramTool."""
    
    def test_import(self):
        from praisonai_tools import TelegramTool
        assert TelegramTool is not None
    
    def test_instantiation(self):
        from praisonai_tools import TelegramTool
        tool = TelegramTool()
        assert tool.name == "telegram"
    
    def test_send_without_chat_id(self):
        from praisonai_tools import TelegramTool
        tool = TelegramTool(chat_id=None)
        result = tool.send_message(text="Test")
        assert "error" in result


class TestNotionTool:
    """Tests for NotionTool."""
    
    def test_import(self):
        from praisonai_tools import NotionTool
        assert NotionTool is not None
    
    def test_instantiation(self):
        from praisonai_tools import NotionTool
        tool = NotionTool()
        assert tool.name == "notion"
    
    def test_search_without_api_key(self):
        from praisonai_tools import NotionTool
        tool = NotionTool(api_key=None)
        result = tool.search()
        assert result[0].get("error") is not None


class TestPostgresTool:
    """Tests for PostgresTool."""
    
    def test_import(self):
        from praisonai_tools import PostgresTool
        assert PostgresTool is not None
    
    def test_instantiation(self):
        from praisonai_tools import PostgresTool
        tool = PostgresTool()
        assert tool.name == "postgres"
    
    def test_query_without_sql(self):
        from praisonai_tools import PostgresTool
        tool = PostgresTool()
        result = tool.query(sql=None)
        assert result[0].get("error") is not None


class TestRedditTool:
    """Tests for RedditTool."""
    
    def test_import(self):
        from praisonai_tools import RedditTool
        assert RedditTool is not None
    
    def test_instantiation(self):
        from praisonai_tools import RedditTool
        tool = RedditTool()
        assert tool.name == "reddit"


class TestDockerTool:
    """Tests for DockerTool."""
    
    def test_import(self):
        from praisonai_tools import DockerTool
        assert DockerTool is not None
    
    def test_instantiation(self):
        from praisonai_tools import DockerTool
        tool = DockerTool()
        assert tool.name == "docker"


class TestBaseToolIntegration:
    """Tests for BaseTool integration."""
    
    def test_all_tools_inherit_basetool(self):
        from praisonai_tools import (
            BaseTool, EmailTool, SlackTool, DiscordTool,
            GitHubTool, ImageTool, WeatherTool, YouTubeTool, TTSTool,
            TelegramTool, NotionTool, PostgresTool, RedditTool, DockerTool
        )
        
        assert issubclass(EmailTool, BaseTool)
        assert issubclass(SlackTool, BaseTool)
        assert issubclass(DiscordTool, BaseTool)
        assert issubclass(GitHubTool, BaseTool)
        assert issubclass(ImageTool, BaseTool)
        assert issubclass(WeatherTool, BaseTool)
        assert issubclass(YouTubeTool, BaseTool)
        assert issubclass(TTSTool, BaseTool)
        assert issubclass(TelegramTool, BaseTool)
        assert issubclass(NotionTool, BaseTool)
        assert issubclass(PostgresTool, BaseTool)
        assert issubclass(RedditTool, BaseTool)
        assert issubclass(DockerTool, BaseTool)
    
    def test_all_tools_have_run_method(self):
        from praisonai_tools import (
            EmailTool, SlackTool, DiscordTool,
            GitHubTool, ImageTool, WeatherTool, YouTubeTool, TTSTool,
            TelegramTool, NotionTool, PostgresTool, RedditTool, DockerTool
        )
        
        tools = [
            EmailTool(), SlackTool(), DiscordTool(),
            GitHubTool(), ImageTool(), WeatherTool(), YouTubeTool(), TTSTool(),
            TelegramTool(), NotionTool(), PostgresTool(), RedditTool(), DockerTool()
        ]
        
        for tool in tools:
            assert hasattr(tool, "run")
            assert callable(tool.run)
    
    def test_all_tools_have_schema(self):
        from praisonai_tools import (
            EmailTool, SlackTool, DiscordTool,
            GitHubTool, ImageTool, WeatherTool, YouTubeTool, TTSTool,
            TelegramTool, NotionTool, PostgresTool, RedditTool, DockerTool
        )
        
        tools = [
            EmailTool(), SlackTool(), DiscordTool(),
            GitHubTool(), ImageTool(), WeatherTool(), YouTubeTool(), TTSTool(),
            TelegramTool(), NotionTool(), PostgresTool(), RedditTool(), DockerTool()
        ]
        
        for tool in tools:
            schema = tool.get_schema()
            assert "type" in schema
            assert "function" in schema
            assert "name" in schema["function"]
            assert "description" in schema["function"]
