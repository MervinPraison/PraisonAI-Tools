"""Tests for SwarmScore tool integration."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from praisonai_tools.tools.swarmscore_tool import (
    SwarmScoreTool,
    load_swarmscore_by_slug,
    verify_swarmscore_freshness,
    get_agent_discovery_manifest
)
from praisonai_tools.tools.base import ToolResult


class TestSwarmScoreTool:
    """Test cases for SwarmScoreTool class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = SwarmScoreTool()
        self.sample_score_data = {
            "score": 85,
            "tier": "gold",
            "jobs_completed": 150,
            "success_rate": 94.5,
            "verify_payload": {
                "signature": "test_signature",
                "timestamp": "2024-01-15T10:30:00Z",
                "agent_id": "test-agent-123"
            }
        }
    
    @patch('praisonai_tools.tools.swarmscore_tool.requests')
    def test_load_swarmscore_success(self, mock_requests):
        """Test successful SwarmScore loading."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = self.sample_score_data
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response
        
        # Execute
        result = self.tool.load_swarmscore("test-agent")
        
        # Verify
        assert result.success is True
        assert result.data == self.sample_score_data
        assert "test-agent" in result.message
        mock_requests.get.assert_called_once()
    
    @patch('praisonai_tools.tools.swarmscore_tool.requests')
    def test_load_swarmscore_network_error(self, mock_requests):
        """Test SwarmScore loading with network error."""
        # Setup mock to raise exception
        mock_requests.get.side_effect = Exception("Network error")
        
        # Execute
        result = self.tool.load_swarmscore("test-agent")
        
        # Verify
        assert result.success is False
        assert "Network error" in result.error
    
    @patch('praisonai_tools.tools.swarmscore_tool.requests')
    def test_load_swarmscore_invalid_json(self, mock_requests):
        """Test SwarmScore loading with invalid JSON response."""
        # Setup mock response with invalid JSON
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response
        
        # Execute
        result = self.tool.load_swarmscore("test-agent")
        
        # Verify
        assert result.success is False
        assert "Invalid response format" in result.error
    
    @patch('praisonai_tools.tools.swarmscore_tool.requests')
    def test_verify_swarmscore_success(self, mock_requests):
        """Test successful SwarmScore verification."""
        # Setup mock response
        verify_data = {"verified": True, "timestamp": "2024-01-15T10:30:00Z"}
        mock_response = Mock()
        mock_response.json.return_value = verify_data
        mock_response.raise_for_status.return_value = None
        mock_requests.post.return_value = mock_response
        
        # Execute
        verify_payload = self.sample_score_data["verify_payload"]
        result = self.tool.verify_swarmscore(verify_payload)
        
        # Verify
        assert result.success is True
        assert result.data == verify_data
        mock_requests.post.assert_called_once()
    
    @patch('praisonai_tools.tools.swarmscore_tool.requests')
    def test_verify_swarmscore_error(self, mock_requests):
        """Test SwarmScore verification with error."""
        # Setup mock to raise exception
        mock_requests.post.side_effect = Exception("Verification failed")
        
        # Execute
        result = self.tool.verify_swarmscore({"test": "payload"})
        
        # Verify
        assert result.success is False
        assert "Verification failed" in result.error
    
    @patch('praisonai_tools.tools.swarmscore_tool.requests')
    def test_get_discovery_manifest_success(self, mock_requests):
        """Test successful discovery manifest retrieval."""
        # Setup mock response
        manifest_data = {
            "agents": ["agent1", "agent2"],
            "capabilities": ["trading", "analysis"],
            "version": "1.0"
        }
        mock_response = Mock()
        mock_response.json.return_value = manifest_data
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response
        
        # Execute
        result = self.tool.get_discovery_manifest()
        
        # Verify
        assert result.success is True
        assert result.data == manifest_data
        mock_requests.get.assert_called_once()
    
    @patch('praisonai_tools.tools.swarmscore_tool.requests')
    def test_get_discovery_manifest_error(self, mock_requests):
        """Test discovery manifest retrieval with error."""
        # Setup mock to raise exception
        mock_requests.get.side_effect = Exception("Manifest error")
        
        # Execute
        result = self.tool.get_discovery_manifest()
        
        # Verify
        assert result.success is False
        assert "Manifest error" in result.error
    
    def test_run_load_action(self):
        """Test run method with load action."""
        with patch.object(self.tool, 'load_swarmscore') as mock_load:
            mock_load.return_value = ToolResult(success=True, data=self.sample_score_data)
            
            result = self.tool.run("load", slug="test-agent")
            
            assert result.success is True
            mock_load.assert_called_once_with("test-agent")
    
    def test_run_verify_action(self):
        """Test run method with verify action."""
        with patch.object(self.tool, 'verify_swarmscore') as mock_verify:
            mock_verify.return_value = ToolResult(success=True, data={"verified": True})
            
            verify_payload = {"test": "payload"}
            result = self.tool.run("verify", verify_payload=verify_payload)
            
            assert result.success is True
            mock_verify.assert_called_once_with(verify_payload)
    
    def test_run_discover_action(self):
        """Test run method with discover action."""
        with patch.object(self.tool, 'get_discovery_manifest') as mock_discover:
            mock_discover.return_value = ToolResult(success=True, data={"agents": []})
            
            result = self.tool.run("discover")
            
            assert result.success is True
            mock_discover.assert_called_once()
    
    def test_run_invalid_action(self):
        """Test run method with invalid action."""
        result = self.tool.run("invalid_action")
        
        assert result.success is False
        assert "Unknown action" in result.error
    
    def test_run_missing_parameters(self):
        """Test run method with missing required parameters."""
        # Test load without slug
        result = self.tool.run("load")
        assert result.success is False
        assert "Missing required parameter 'slug'" in result.error
        
        # Test verify without verify_payload
        result = self.tool.run("verify")
        assert result.success is False
        assert "Missing required parameter 'verify_payload'" in result.error


class TestStandaloneFunctions:
    """Test cases for standalone utility functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_data = {
            "score": 75,
            "tier": "silver",
            "verify_payload": {"test": "payload"}
        }
    
    @patch('praisonai_tools.tools.swarmscore_tool.SwarmScoreTool')
    def test_load_swarmscore_by_slug_success(self, mock_tool_class):
        """Test successful standalone load function."""
        # Setup mock
        mock_tool = Mock()
        mock_tool.load_swarmscore.return_value = ToolResult(
            success=True, 
            data=self.sample_data
        )
        mock_tool_class.return_value = mock_tool
        
        # Execute
        result = load_swarmscore_by_slug("test-agent")
        
        # Verify
        assert result == self.sample_data
        mock_tool.load_swarmscore.assert_called_once_with("test-agent")
    
    @patch('praisonai_tools.tools.swarmscore_tool.SwarmScoreTool')
    def test_load_swarmscore_by_slug_failure(self, mock_tool_class):
        """Test standalone load function with failure."""
        # Setup mock
        mock_tool = Mock()
        mock_tool.load_swarmscore.return_value = ToolResult(
            success=False, 
            error="Load failed"
        )
        mock_tool_class.return_value = mock_tool
        
        # Execute and verify exception
        with pytest.raises(Exception, match="Load failed"):
            load_swarmscore_by_slug("test-agent")
    
    @patch('praisonai_tools.tools.swarmscore_tool.SwarmScoreTool')
    def test_verify_swarmscore_freshness_success(self, mock_tool_class):
        """Test successful standalone verify function."""
        # Setup mock
        verify_data = {"verified": True}
        mock_tool = Mock()
        mock_tool.verify_swarmscore.return_value = ToolResult(
            success=True, 
            data=verify_data
        )
        mock_tool_class.return_value = mock_tool
        
        # Execute
        payload = {"test": "payload"}
        result = verify_swarmscore_freshness(payload)
        
        # Verify
        assert result == verify_data
        mock_tool.verify_swarmscore.assert_called_once_with(payload)
    
    @patch('praisonai_tools.tools.swarmscore_tool.SwarmScoreTool')
    def test_verify_swarmscore_freshness_failure(self, mock_tool_class):
        """Test standalone verify function with failure."""
        # Setup mock
        mock_tool = Mock()
        mock_tool.verify_swarmscore.return_value = ToolResult(
            success=False, 
            error="Verification failed"
        )
        mock_tool_class.return_value = mock_tool
        
        # Execute and verify exception
        with pytest.raises(Exception, match="Verification failed"):
            verify_swarmscore_freshness({"test": "payload"})
    
    @patch('praisonai_tools.tools.swarmscore_tool.SwarmScoreTool')
    def test_get_agent_discovery_manifest_success(self, mock_tool_class):
        """Test successful standalone discovery function."""
        # Setup mock
        manifest_data = {"agents": ["test1", "test2"]}
        mock_tool = Mock()
        mock_tool.get_discovery_manifest.return_value = ToolResult(
            success=True, 
            data=manifest_data
        )
        mock_tool_class.return_value = mock_tool
        
        # Execute
        result = get_agent_discovery_manifest()
        
        # Verify
        assert result == manifest_data
        mock_tool.get_discovery_manifest.assert_called_once()
    
    @patch('praisonai_tools.tools.swarmscore_tool.SwarmScoreTool')
    def test_get_agent_discovery_manifest_failure(self, mock_tool_class):
        """Test standalone discovery function with failure."""
        # Setup mock
        mock_tool = Mock()
        mock_tool.get_discovery_manifest.return_value = ToolResult(
            success=False, 
            error="Discovery failed"
        )
        mock_tool_class.return_value = mock_tool
        
        # Execute and verify exception
        with pytest.raises(Exception, match="Discovery failed"):
            get_agent_discovery_manifest()


class TestToolInitialization:
    """Test tool initialization and dependencies."""
    
    def test_tool_initialization_default(self):
        """Test tool initialization with default parameters."""
        tool = SwarmScoreTool()
        assert "api.swarmsync.ai" in tool.api_base_url
        assert not tool.api_base_url.endswith('/')
    
    def test_tool_initialization_custom_url(self):
        """Test tool initialization with custom URL."""
        custom_url = "https://custom.api.com/v1/swarmscore/"
        tool = SwarmScoreTool(api_base_url=custom_url)
        assert tool.api_base_url == "https://custom.api.com/v1/swarmscore"
    
    @patch('praisonai_tools.tools.swarmscore_tool.requests', None)
    def test_tool_initialization_missing_requests(self):
        """Test tool initialization without requests library."""
        with pytest.raises(ImportError, match="requests is required"):
            SwarmScoreTool()


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    @patch('praisonai_tools.tools.swarmscore_tool.requests')
    def test_full_workflow_success(self, mock_requests):
        """Test complete workflow: load -> verify -> discover."""
        tool = SwarmScoreTool()
        
        # Setup mock responses
        load_data = {
            "score": 90,
            "tier": "platinum",
            "verify_payload": {"signature": "test123"}
        }
        verify_data = {"verified": True}
        manifest_data = {"agents": ["agent1"]}
        
        mock_responses = [
            Mock(json=lambda: load_data, raise_for_status=lambda: None),
            Mock(json=lambda: verify_data, raise_for_status=lambda: None),
            Mock(json=lambda: manifest_data, raise_for_status=lambda: None)
        ]
        
        # Configure mock to return different responses for different calls
        mock_requests.get.side_effect = [mock_responses[0], mock_responses[2]]
        mock_requests.post.return_value = mock_responses[1]
        
        # Execute workflow
        load_result = tool.load_swarmscore("test-agent")
        assert load_result.success is True
        assert load_result.data["score"] == 90
        
        verify_result = tool.verify_swarmscore(load_data["verify_payload"])
        assert verify_result.success is True
        assert verify_result.data["verified"] is True
        
        manifest_result = tool.get_discovery_manifest()
        assert manifest_result.success is True
        assert "agent1" in manifest_result.data["agents"]
    
    @patch('praisonai_tools.tools.swarmscore_tool.requests')
    def test_error_recovery(self, mock_requests):
        """Test graceful error handling and recovery."""
        tool = SwarmScoreTool()
        
        # First call fails, second succeeds
        mock_requests.get.side_effect = [
            Exception("Network timeout"),
            Mock(
                json=lambda: {"score": 80}, 
                raise_for_status=lambda: None
            )
        ]
        
        # First attempt fails
        result1 = tool.load_swarmscore("test-agent")
        assert result1.success is False
        assert "Network timeout" in result1.error
        
        # Second attempt succeeds
        result2 = tool.load_swarmscore("test-agent")
        assert result2.success is True
        assert result2.data["score"] == 80