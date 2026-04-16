"""Unit tests for n8n integration tools."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestN8nWorkflowTool:
    """Test the N8nWorkflowTool class."""
    
    @pytest.fixture
    def mock_httpx(self):
        """Mock httpx module for testing."""
        mock_module = MagicMock()
        
        # Create proper exception classes
        mock_module.TimeoutException = type('TimeoutException', (Exception,), {})
        
        class MockHTTPStatusError(Exception):
            def __init__(self, message, request=None, response=None):
                super().__init__(message)
                self.request = request
                self.response = response
        
        mock_module.HTTPStatusError = MockHTTPStatusError
        
        with patch.dict('sys.modules', {'httpx': mock_module}) as mock_modules:
            yield mock_module
    
    def test_import_n8n_tools(self):
        """Test that n8n tools can be imported."""
        try:
            from praisonai_tools.n8n import n8n_workflow, N8nWorkflowTool
            assert callable(n8n_workflow)
            assert N8nWorkflowTool is not None
        except ImportError as e:
            pytest.fail(f"Failed to import n8n tools: {e}")
    
    def test_n8n_workflow_tool_init(self):
        """Test N8nWorkflowTool initialization."""
        from praisonai_tools.n8n import N8nWorkflowTool
        
        # Test with default values
        tool = N8nWorkflowTool()
        assert tool.n8n_url == "http://localhost:5678"
        assert tool.api_key is None
        assert tool.timeout == 60.0
        
        # Test with custom values
        tool = N8nWorkflowTool(
            n8n_url="https://my-n8n.com",
            api_key="test-key",
            timeout=30.0
        )
        assert tool.n8n_url == "https://my-n8n.com"
        assert tool.api_key == "test-key"
        assert tool.timeout == 30.0
    
    def test_n8n_workflow_tool_env_vars(self):
        """Test N8nWorkflowTool reads environment variables."""
        from praisonai_tools.n8n import N8nWorkflowTool
        
        with patch.dict(os.environ, {
            'N8N_URL': 'https://env-n8n.com',
            'N8N_API_KEY': 'env-api-key'
        }):
            tool = N8nWorkflowTool()
            assert tool.n8n_url == "https://env-n8n.com"
            assert tool.api_key == "env-api-key"
    
    def test_n8n_workflow_missing_workflow_id(self):
        """Test error handling when workflow_id is missing."""
        from praisonai_tools.n8n import N8nWorkflowTool
        
        tool = N8nWorkflowTool()
        result = tool.run(workflow_id="")
        assert result["error"] == "workflow_id is required"
    
    def test_n8n_workflow_missing_httpx(self):
        """Test error handling when httpx is not installed."""
        from praisonai_tools.n8n import N8nWorkflowTool
        
        tool = N8nWorkflowTool()
        # Mock the import failure using sys.modules approach
        with patch.dict('sys.modules', {'httpx': None}):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'httpx'")):
                result = tool.run(workflow_id="test-workflow")
                assert "httpx not installed" in result["error"]
                assert "pip install 'praisonai-tools[n8n]'" in result["error"]
    
    def test_n8n_workflow_successful_execution(self, mock_httpx):
        """Test successful workflow execution via webhook."""
        from praisonai_tools.n8n import N8nWorkflowTool
        
        # Mock workflow fetch response
        mock_workflow_response = Mock()
        mock_workflow_response.json.return_value = {
            "id": "test-workflow",
            "name": "Test Workflow",
            "active": True,
            "nodes": [
                {
                    "id": "webhook-node",
                    "name": "Webhook",
                    "type": "n8n-nodes-base.webhook",
                    "parameters": {
                        "path": "test-webhook",
                        "httpMethod": "POST"
                    }
                }
            ]
        }
        mock_workflow_response.raise_for_status.return_value = None
        
        # Mock webhook execution response
        mock_webhook_response = Mock()
        mock_webhook_response.json.return_value = {
            "result": "success",
            "message": "Webhook executed successfully"
        }
        mock_webhook_response.raise_for_status.return_value = None
        
        mock_client = Mock()
        mock_client.get.return_value = mock_workflow_response
        mock_client.post.return_value = mock_webhook_response
        mock_httpx.Client.return_value.__enter__.return_value = mock_client
        
        tool = N8nWorkflowTool(api_key="test-key")
        result = tool.run(
            workflow_id="test-workflow",
            input_data={"message": "Hello"},
            wait_for_completion=False
        )
        
        assert result["result"] == "success"
        assert result["message"] == "Webhook executed successfully"
        
        # Verify workflow fetch call
        mock_client.get.assert_called_once_with(
            "http://localhost:5678/api/v1/workflows/test-workflow",
            headers={"Content-Type": "application/json", "X-N8N-API-KEY": "test-key"},
        )
        
        # Verify webhook execution call
        mock_client.post.assert_called_once_with(
            "http://localhost:5678/webhook/test-webhook",
            json={"message": "Hello"},
            headers={"Content-Type": "application/json"},
        )
    
    def test_n8n_workflow_http_error(self, mock_httpx):
        """Test HTTP error handling during workflow fetch."""
        from praisonai_tools.n8n import N8nWorkflowTool
        
        # Mock HTTP error during workflow fetch
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        mock_client = Mock()
        mock_client.get.side_effect = mock_httpx.HTTPStatusError(
            "401 Unauthorized", request=Mock(), response=mock_response
        )
        mock_httpx.Client.return_value.__enter__.return_value = mock_client
        
        tool = N8nWorkflowTool(api_key="invalid-key")
        result = tool.run(workflow_id="test-workflow")
        
        assert "HTTP 401: Unauthorized" in result["error"]
    
    def test_n8n_workflow_timeout_error(self, mock_httpx):
        """Test timeout error handling during workflow fetch."""
        from praisonai_tools.n8n import N8nWorkflowTool
        
        mock_client = Mock()
        mock_client.get.side_effect = mock_httpx.TimeoutException("Request timed out")
        mock_httpx.Client.return_value.__enter__.return_value = mock_client
        
        tool = N8nWorkflowTool(timeout=5.0)
        result = tool.run(workflow_id="test-workflow")
        
        assert "timed out after 5.0 seconds" in result["error"]
    
    def test_n8n_workflow_no_webhook_trigger(self, mock_httpx):
        """Test error handling when workflow has no webhook trigger."""
        from praisonai_tools.n8n import N8nWorkflowTool
        
        # Mock workflow fetch response with no webhook trigger
        mock_workflow_response = Mock()
        mock_workflow_response.json.return_value = {
            "id": "test-workflow",
            "name": "Test Workflow",
            "active": True,
            "nodes": [
                {
                    "id": "manual-node",
                    "name": "Manual Trigger",
                    "type": "n8n-nodes-base.manualTrigger",
                    "parameters": {}
                }
            ]
        }
        mock_workflow_response.raise_for_status.return_value = None
        
        mock_client = Mock()
        mock_client.get.return_value = mock_workflow_response
        mock_httpx.Client.return_value.__enter__.return_value = mock_client
        
        tool = N8nWorkflowTool(api_key="test-key")
        result = tool.run(workflow_id="test-workflow")
        
        assert "Workflow has no Webhook trigger node" in result["error"]
    
    def test_n8n_list_workflows(self, mock_httpx):
        """Test listing workflows."""
        from praisonai_tools.n8n import N8nWorkflowTool
        
        # Mock httpx response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"id": "workflow-1", "name": "My Workflow 1"},
                {"id": "workflow-2", "name": "My Workflow 2"},
            ]
        }
        mock_response.raise_for_status.return_value = None
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_httpx.Client.return_value.__enter__.return_value = mock_client
        
        tool = N8nWorkflowTool(api_key="test-key")
        result = tool.list_workflows()
        
        assert "data" in result
        assert len(result["data"]) == 2
        assert result["data"][0]["name"] == "My Workflow 1"
        
        # Verify API call
        mock_client.get.assert_called_once_with(
            "http://localhost:5678/api/v1/workflows",
            headers={"Content-Type": "application/json", "X-N8N-API-KEY": "test-key"},
        )


class TestN8nWorkflowFunction:
    """Test the n8n_workflow function."""
    
    @patch('praisonai_tools.n8n.n8n_workflow.N8nWorkflowTool')
    def test_n8n_workflow_function_calls_tool(self, mock_tool_class):
        """Test that n8n_workflow function creates tool and calls run method."""
        from praisonai_tools.n8n import n8n_workflow
        
        # Mock tool instance
        mock_tool = Mock()
        mock_tool.run.return_value = {"result": "success"}
        mock_tool_class.return_value = mock_tool
        
        result = n8n_workflow(
            workflow_id="test-workflow",
            input_data={"key": "value"},
            n8n_url="https://custom.n8n.com",
            api_key="custom-key",
            timeout=30.0
        )
        
        # Verify tool was created with correct parameters
        mock_tool_class.assert_called_once_with(
            n8n_url="https://custom.n8n.com",
            api_key="custom-key",
            timeout=30.0
        )
        
        # Verify run was called with correct parameters
        mock_tool.run.assert_called_once_with(
            workflow_id="test-workflow",
            input_data={"key": "value"},
            wait_for_completion=True
        )
        
        assert result == {"result": "success"}


class TestN8nListWorkflowsFunction:
    """Test the n8n_list_workflows function."""
    
    @patch('praisonai_tools.n8n.n8n_workflow.N8nWorkflowTool')
    def test_n8n_list_workflows_function(self, mock_tool_class):
        """Test that n8n_list_workflows function works correctly."""
        from praisonai_tools.n8n import n8n_list_workflows
        
        # Mock tool instance
        mock_tool = Mock()
        mock_tool.list_workflows.return_value = {"workflows": ["workflow-1"]}
        mock_tool_class.return_value = mock_tool
        
        result = n8n_list_workflows(
            n8n_url="https://test.n8n.com",
            api_key="test-key"
        )
        
        # Verify tool was created correctly
        mock_tool_class.assert_called_once_with(
            n8n_url="https://test.n8n.com",
            api_key="test-key"
        )
        
        # Verify list_workflows was called
        mock_tool.list_workflows.assert_called_once()
        
        assert result == {"workflows": ["workflow-1"]}


@pytest.mark.integration
class TestN8nIntegration:
    """Integration tests for n8n tools (requires running n8n instance)."""
    
    @pytest.fixture
    def n8n_config(self):
        """Get n8n configuration from environment or skip test."""
        n8n_url = os.getenv("N8N_URL")
        if not n8n_url:
            pytest.skip("N8N_URL environment variable not set")
        
        return {
            "n8n_url": n8n_url,
            "api_key": os.getenv("N8N_API_KEY"),  # Optional for local testing
        }
    
    def test_list_workflows_integration(self, n8n_config):
        """Test listing workflows against real n8n instance."""
        from praisonai_tools.n8n import n8n_list_workflows
        
        result = n8n_list_workflows(**n8n_config)
        
        # Should not have an error key if successful
        assert "error" not in result
        # Should return some data structure
        assert isinstance(result, dict)
    
    def test_workflow_execution_integration(self, n8n_config):
        """Test workflow execution against real n8n instance."""
        from praisonai_tools.n8n import n8n_workflow
        
        # Skip if no test workflow ID provided
        test_workflow_id = os.getenv("N8N_TEST_WORKFLOW_ID")
        if not test_workflow_id:
            pytest.skip("N8N_TEST_WORKFLOW_ID environment variable not set")
        
        result = n8n_workflow(
            workflow_id=test_workflow_id,
            input_data={"test": "integration"},
            **n8n_config
        )
        
        # Should not have an error key if successful
        assert "error" not in result
        # Should return some execution data
        assert isinstance(result, dict)


def test_n8n_smoke_test():
    """Smoke test to verify n8n tools can be imported without errors."""
    try:
        from praisonai_tools.n8n import n8n_workflow, n8n_list_workflows, N8nWorkflowTool
        
        # Test that they are callable/instantiable
        assert callable(n8n_workflow)
        assert callable(n8n_list_workflows)
        assert N8nWorkflowTool is not None
        
        # Test basic instantiation
        tool = N8nWorkflowTool()
        assert tool.name == "n8n_workflow"
        assert "n8n" in tool.description.lower()
        
    except Exception as e:
        pytest.fail(f"n8n tools smoke test failed: {e}")


if __name__ == "__main__":
    # Run smoke test when executed directly
    test_n8n_smoke_test()
    print("✅ n8n tools smoke test passed")