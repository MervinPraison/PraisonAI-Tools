"""Tests for LLM Tool."""

import os
import pytest
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_tool import LLMTool, LLMResponse, llm_complete


class TestLLMTool:
    """Test LLMTool class."""
    
    def test_init_default(self):
        """Test default initialization."""
        tool = LLMTool()
        assert tool.provider == "openai"
        assert tool.model == "gpt-4o-mini"
        assert tool.temperature == 0.7
        assert tool.max_tokens == 4096
    
    def test_init_custom(self):
        """Test custom initialization."""
        tool = LLMTool(
            provider="anthropic",
            model="claude-3-haiku",
            temperature=0.5,
            max_tokens=2048,
        )
        assert tool.provider == "anthropic"
        assert tool.model == "claude-3-haiku"
        assert tool.temperature == 0.5
        assert tool.max_tokens == 2048
    
    def test_default_model(self):
        """Test default model selection."""
        openai_tool = LLMTool(provider="openai")
        assert openai_tool.model == "gpt-4o-mini"
        
        anthropic_tool = LLMTool(provider="anthropic")
        assert anthropic_tool.model == "claude-3-haiku-20240307"
        
        google_tool = LLMTool(provider="google")
        assert google_tool.model == "gemini-1.5-flash"
    
    def test_check_dependencies_openai(self):
        """Test dependency check for OpenAI."""
        tool = LLMTool(provider="openai")
        deps = tool.check_dependencies()
        assert "openai" in deps
        assert "api_key" in deps
    
    @pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
    def test_complete_openai(self):
        """Test completion with OpenAI."""
        tool = LLMTool(provider="openai")
        response = tool.complete("Say 'test' and nothing else", max_tokens=10)
        
        assert response.success
        assert response.content
        assert response.model
        assert response.provider == "openai"
        assert response.usage
    
    @pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
    def test_complete_with_system(self):
        """Test completion with system message."""
        tool = LLMTool(provider="openai")
        response = tool.complete(
            "What are you?",
            system="You are a helpful robot. Always respond with 'I am a robot.'",
            max_tokens=20,
        )
        
        assert response.success
        assert "robot" in response.content.lower()
    
    @pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
    def test_extract_json(self):
        """Test JSON extraction."""
        tool = LLMTool(provider="openai")
        schema = {"name": "string", "age": "number"}
        
        result = tool.extract_json(
            "Extract: John is 30 years old",
            schema=schema,
        )
        
        assert isinstance(result, dict)
        assert "name" in result or "age" in result


class TestLLMResponse:
    """Test LLMResponse dataclass."""
    
    def test_response_creation(self):
        """Test response creation."""
        response = LLMResponse(
            success=True,
            content="Hello",
            model="gpt-4o-mini",
            provider="openai",
            usage={"total_tokens": 10},
            finish_reason="stop",
        )
        
        assert response.success
        assert response.content == "Hello"
        assert response.model == "gpt-4o-mini"
        assert response.provider == "openai"
        assert response.usage["total_tokens"] == 10


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
    def test_llm_complete(self):
        """Test llm_complete function."""
        result = llm_complete("Say 'hello'", max_tokens=10)
        assert isinstance(result, str)
        assert len(result) > 0
