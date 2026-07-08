"""Tests for NEXUS Prediction Market Tool"""

import pytest
import json
import requests
from unittest.mock import Mock, patch
from praisonai_tools.tools.nexus_prediction_market_tool import (
    NexusPredictionMarketTool,
    nexus_prediction_market_tool
)


class TestNexusPredictionMarketTool:
    """Test cases for NEXUS Prediction Market Tool"""
    
    def test_tool_initialization(self):
        """Test tool initialization with default and custom parameters."""
        # Default initialization
        tool = NexusPredictionMarketTool()
        assert tool.name == "nexus_prediction_market"
        assert tool.source_name == "praisonai-agent"
        assert "X-NEXUS-Source" in tool.headers
        assert tool.base_url == "https://nexus-agent-xa12.onrender.com"
        
        # Custom initialization
        custom_tool = NexusPredictionMarketTool(
            source_name="test-bot",
            api_key="test-key"
        )
        assert custom_tool.source_name == "test-bot"
        assert custom_tool.headers["X-NEXUS-Source"] == "test-bot"
        assert "Authorization" in custom_tool.headers
    
    @patch('praisonai_tools.tools.nexus_prediction_market_tool.requests.get')
    def test_get_market_data_success(self, mock_get):
        """Test successful market data retrieval."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "market": "Fed",
            "price": 0.75,
            "volume": 1000000,
            "trend": "bullish"
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        tool = NexusPredictionMarketTool()
        result = tool.get_market_data("Fed")
        
        assert result["success"] is True
        assert result["market"] == "Fed"
        assert "data" in result
        assert result["source"] == "nexus-free-api"
        
        # Verify request was made correctly
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "kalshi" in args[0]
        assert kwargs["params"]["market"] == "Fed"
        assert "X-NEXUS-Source" in kwargs["headers"]
    
    @patch('praisonai_tools.tools.nexus_prediction_market_tool.requests.get')
    def test_get_market_data_failure(self, mock_get):
        """Test market data retrieval failure."""
        # Mock failed response
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
        
        tool = NexusPredictionMarketTool()
        result = tool.get_market_data("Fed")
        
        assert result["success"] is False
        assert "error" in result
        assert result["market"] == "Fed"
    
    @patch('praisonai_tools.tools.nexus_prediction_market_tool.requests.get')
    def test_check_arbitrage_opportunities_success(self, mock_get):
        """Test successful arbitrage checking."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "opportunities": [
                {
                    "markets": ["Fed", "BTC"],
                    "profit_potential": 0.05,
                    "risk_level": "medium"
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        tool = NexusPredictionMarketTool()
        result = tool.check_arbitrage_opportunities(["Fed", "BTC"])
        
        assert result["success"] is True
        assert result["markets"] == ["Fed", "BTC"]
        assert "arbitrage_data" in result
        assert result["source"] == "nexus-paid-api"
        
        # Verify request was made correctly
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "arb/check" in args[0]
        assert kwargs["params"]["markets"] == "Fed,BTC"
    
    @patch('praisonai_tools.tools.nexus_prediction_market_tool.requests.get')
    def test_check_arbitrage_payment_required(self, mock_get):
        """Test arbitrage checking when payment is required."""
        # Mock payment required response
        mock_response = Mock()
        mock_response.status_code = 402
        http_error = requests.exceptions.HTTPError("Payment Required")
        http_error.response = mock_response
        mock_get.side_effect = http_error
        
        tool = NexusPredictionMarketTool()
        result = tool.check_arbitrage_opportunities(["Fed", "BTC"])
        
        assert result["success"] is False
        assert "payment required" in result["error"].lower()
        assert result["markets"] == ["Fed", "BTC"]
    
    @patch('praisonai_tools.tools.nexus_prediction_market_tool.requests.get')
    def test_get_agent_info_success(self, mock_get):
        """Test successful agent info retrieval."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "NEXUS",
            "description": "Prediction market data API",
            "version": "1.0"
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        tool = NexusPredictionMarketTool()
        result = tool.get_agent_info()
        
        assert result["success"] is True
        assert "agent_info" in result
        assert result["source"] == "nexus-agent-metadata"
        
        # Verify request was made correctly
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert ".well-known/agent.json" in args[0]
    
    def test_run_method_get_market_data(self):
        """Test run method with get_market_data action."""
        tool = NexusPredictionMarketTool()
        
        with patch.object(tool, 'get_market_data') as mock_method:
            mock_method.return_value = {"success": True, "test": "data"}
            
            result = tool.run("get_market_data", market="Fed")
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            mock_method.assert_called_once_with("Fed")
    
    def test_run_method_check_arbitrage(self):
        """Test run method with check_arbitrage action."""
        tool = NexusPredictionMarketTool()
        
        with patch.object(tool, 'check_arbitrage_opportunities') as mock_method:
            mock_method.return_value = {"success": True, "test": "data"}
            
            result = tool.run("check_arbitrage", markets=["Fed", "BTC"])
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            mock_method.assert_called_once_with(["Fed", "BTC"])
    
    def test_run_method_get_agent_info(self):
        """Test run method with get_agent_info action."""
        tool = NexusPredictionMarketTool()
        
        with patch.object(tool, 'get_agent_info') as mock_method:
            mock_method.return_value = {"success": True, "test": "data"}
            
            result = tool.run("get_agent_info")
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            mock_method.assert_called_once()
    
    def test_run_method_invalid_action(self):
        """Test run method with invalid action."""
        tool = NexusPredictionMarketTool()
        
        result = tool.run("invalid_action")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "unknown action" in result_data["error"].lower()
    
    def test_run_method_missing_parameters(self):
        """Test run method with missing required parameters."""
        tool = NexusPredictionMarketTool()
        
        # Missing market parameter
        result = tool.run("get_market_data")
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "market parameter required" in result_data["error"].lower()
        
        # Missing markets parameter  
        result = tool.run("check_arbitrage")
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "markets parameter" in result_data["error"].lower()


class TestNexusPredictionMarketFunction:
    """Test cases for the function-based interface"""
    
    def test_function_interface(self):
        """Test the function-based interface."""
        with patch('praisonai_tools.tools.nexus_prediction_market_tool.NexusPredictionMarketTool') as mock_class:
            mock_instance = Mock()
            mock_instance.run.return_value = '{"success": true}'
            mock_class.return_value = mock_instance
            
            result = nexus_prediction_market_tool(
                action="get_market_data",
                market="Fed",
                source_name="test-source"
            )
            
            assert result == '{"success": true}'
            mock_class.assert_called_once_with(source_name="test-source")
            mock_instance.run.assert_called_once_with(
                action="get_market_data",
                market="Fed",
                markets=None
            )


if __name__ == "__main__":
    pytest.main([__file__])