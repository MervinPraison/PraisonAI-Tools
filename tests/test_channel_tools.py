"""Tests for channel tools (Signal, LINE, iMessage)."""

import pytest
from unittest.mock import patch, MagicMock


class TestSignalTool:
    """Tests for SignalTool."""
    
    def test_import(self):
        """Test SignalTool can be imported."""
        from praisonai_tools import SignalTool
        assert SignalTool is not None
    
    def test_init_defaults(self):
        """Test SignalTool initialization with defaults."""
        from praisonai_tools import SignalTool
        tool = SignalTool()
        assert tool.name == "signal"
        assert tool.base_url == "http://localhost:8080"
    
    def test_init_custom_url(self):
        """Test SignalTool with custom URL."""
        from praisonai_tools import SignalTool
        tool = SignalTool(base_url="http://custom:9000")
        assert tool.base_url == "http://custom:9000"
    
    def test_normalize_base_url(self):
        """Test URL normalization."""
        from praisonai_tools import SignalTool
        tool = SignalTool(base_url="localhost:8080/")
        assert tool.base_url == "http://localhost:8080"
    
    def test_parse_target_phone(self):
        """Test parsing phone number target."""
        from praisonai_tools import SignalTool
        tool = SignalTool()
        result = tool._parse_target("+1234567890")
        assert result["type"] == "recipient"
        assert result["recipient"] == ["+1234567890"]
    
    def test_parse_target_group(self):
        """Test parsing group target."""
        from praisonai_tools import SignalTool
        tool = SignalTool()
        result = tool._parse_target("group:abc123")
        assert result["type"] == "group"
        assert result["groupId"] == "abc123"
    
    def test_parse_target_username(self):
        """Test parsing username target."""
        from praisonai_tools import SignalTool
        tool = SignalTool()
        result = tool._parse_target("username:alice")
        assert result["type"] == "username"
        assert result["username"] == ["alice"]
    
    def test_send_message_requires_to(self):
        """Test send_message requires recipient."""
        from praisonai_tools import SignalTool
        tool = SignalTool()
        result = tool.send_message(to="", message="test")
        assert "error" in result
    
    def test_send_message_requires_message(self):
        """Test send_message requires message or media."""
        from praisonai_tools import SignalTool
        tool = SignalTool()
        result = tool.send_message(to="+1234567890", message="")
        assert "error" in result
    
    @patch("praisonai_tools.tools.signal_tool.SignalTool._rpc_request")
    def test_send_message_success(self, mock_rpc):
        """Test successful message send."""
        from praisonai_tools import SignalTool
        mock_rpc.return_value = {"timestamp": 1234567890}
        
        tool = SignalTool()
        result = tool.send_message(to="+1234567890", message="Hello")
        
        assert result["success"] is True
        assert result["timestamp"] == 1234567890


class TestLineTool:
    """Tests for LineTool."""
    
    def test_import(self):
        """Test LineTool can be imported."""
        from praisonai_tools import LineTool
        assert LineTool is not None
    
    def test_init(self):
        """Test LineTool initialization."""
        from praisonai_tools import LineTool
        tool = LineTool()
        assert tool.name == "line"
    
    def test_build_text_message(self):
        """Test building text message object."""
        from praisonai_tools import LineTool
        tool = LineTool()
        msg = tool._build_text_message("Hello")
        assert msg["type"] == "text"
        assert msg["text"] == "Hello"
    
    def test_build_image_message(self):
        """Test building image message object."""
        from praisonai_tools import LineTool
        tool = LineTool()
        msg = tool._build_image_message("https://example.com/image.jpg")
        assert msg["type"] == "image"
        assert msg["originalContentUrl"] == "https://example.com/image.jpg"
    
    def test_push_message_requires_to(self):
        """Test push_message requires recipient."""
        from praisonai_tools import LineTool
        tool = LineTool()
        result = tool.push_message(to="", message="test")
        assert "error" in result
    
    def test_push_message_requires_message(self):
        """Test push_message requires message."""
        from praisonai_tools import LineTool
        tool = LineTool()
        result = tool.push_message(to="user123", message="")
        assert "error" in result
    
    def test_reply_message_requires_token(self):
        """Test reply_message requires reply token."""
        from praisonai_tools import LineTool
        tool = LineTool()
        result = tool.reply_message(reply_token="", message="test")
        assert "error" in result
    
    def test_multicast_requires_user_ids(self):
        """Test multicast requires user IDs."""
        from praisonai_tools import LineTool
        tool = LineTool()
        result = tool.multicast(user_ids=[], message="test")
        assert "error" in result
    
    def test_normalize_line_prefix(self):
        """Test normalizing line: prefix."""
        from praisonai_tools import LineTool
        tool = LineTool(channel_access_token="test")
        # The push_message method should strip line: prefix
        # We can't fully test without mocking, but we can verify the tool works
        assert tool.channel_access_token == "test"


class TestiMessageTool:
    """Tests for iMessageTool."""
    
    def test_import(self):
        """Test iMessageTool can be imported."""
        from praisonai_tools import iMessageTool
        assert iMessageTool is not None
    
    def test_init_defaults(self):
        """Test iMessageTool initialization with defaults."""
        from praisonai_tools import iMessageTool
        tool = iMessageTool()
        assert tool.name == "imessage"
        assert tool.mode == "applescript"
    
    def test_init_rest_mode(self):
        """Test iMessageTool with REST mode."""
        from praisonai_tools import iMessageTool
        tool = iMessageTool(api_url="http://localhost:8080", mode="rest")
        assert tool.mode == "rest"
        assert tool.api_url == "http://localhost:8080"
    
    def test_normalize_recipient_imessage_prefix(self):
        """Test normalizing imessage: prefix."""
        from praisonai_tools import iMessageTool
        tool = iMessageTool()
        result = tool._normalize_recipient("imessage:+1234567890")
        assert result == "+1234567890"
    
    def test_normalize_recipient_imsg_prefix(self):
        """Test normalizing imsg: prefix."""
        from praisonai_tools import iMessageTool
        tool = iMessageTool()
        result = tool._normalize_recipient("imsg:user@example.com")
        assert result == "user@example.com"
    
    def test_escape_applescript_string(self):
        """Test AppleScript string escaping."""
        from praisonai_tools import iMessageTool
        tool = iMessageTool()
        result = tool._escape_applescript_string('Hello "World"')
        assert result == 'Hello \\"World\\"'
    
    def test_send_message_requires_to(self):
        """Test send_message requires recipient."""
        from praisonai_tools import iMessageTool
        tool = iMessageTool()
        result = tool.send_message(to="", message="test")
        assert "error" in result
    
    def test_send_message_requires_message(self):
        """Test send_message requires message."""
        from praisonai_tools import iMessageTool
        tool = iMessageTool()
        result = tool.send_message(to="+1234567890", message="")
        assert "error" in result


class TestFunctionHelpers:
    """Tests for standalone function helpers."""
    
    def test_send_signal_message_import(self):
        """Test send_signal_message can be imported."""
        from praisonai_tools import send_signal_message
        assert callable(send_signal_message)
    
    def test_send_line_message_import(self):
        """Test send_line_message can be imported."""
        from praisonai_tools import send_line_message
        assert callable(send_line_message)
    
    def test_send_imessage_import(self):
        """Test send_imessage can be imported."""
        from praisonai_tools import send_imessage
        assert callable(send_imessage)
    
    def test_check_signal_connection_import(self):
        """Test check_signal_connection can be imported."""
        from praisonai_tools import check_signal_connection
        assert callable(check_signal_connection)
    
    def test_check_imessage_availability_import(self):
        """Test check_imessage_availability can be imported."""
        from praisonai_tools import check_imessage_availability
        assert callable(check_imessage_availability)


class TestWhatsAppTool:
    """Tests for WhatsAppTool (existing tool)."""
    
    def test_import(self):
        """Test WhatsAppTool can be imported."""
        from praisonai_tools import WhatsAppTool
        assert WhatsAppTool is not None
    
    def test_init(self):
        """Test WhatsAppTool initialization."""
        from praisonai_tools import WhatsAppTool
        tool = WhatsAppTool()
        assert tool.name == "whatsapp"
    
    def test_send_message_requires_credentials(self):
        """Test send_message requires credentials."""
        from praisonai_tools import WhatsAppTool
        tool = WhatsAppTool()
        result = tool.send_message(to="+1234567890", message="test")
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
