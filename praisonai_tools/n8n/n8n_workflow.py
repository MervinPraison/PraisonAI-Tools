"""n8n Workflow Execution Tool for PraisonAI Agents.

Enables PraisonAI agents to execute n8n workflows, providing access to
n8n's 400+ integrations (Slack, Gmail, Notion, databases, APIs, etc.).

Usage:
    from praisonai_tools.n8n import n8n_workflow
    
    # Execute n8n workflow
    result = n8n_workflow(
        workflow_id="workflow-123",
        input_data={"message": "Hello from PraisonAI"},
        n8n_url="http://localhost:5678",
        api_key="your-api-key"
    )

Environment Variables:
    N8N_URL: n8n instance URL (default: http://localhost:5678)
    N8N_API_KEY: n8n API key for authentication
"""

import os
import logging
from typing import Any, Dict, Optional

from praisonai_tools.tools.base import BaseTool
from praisonai_tools.tools.decorator import tool

logger = logging.getLogger(__name__)


class N8nWorkflowTool(BaseTool):
    """Tool for executing n8n workflows from PraisonAI agents."""
    
    name = "n8n_workflow"
    description = "Execute n8n workflows to access 400+ integrations (Slack, Gmail, Notion, databases, APIs, etc.)"
    
    def __init__(
        self,
        n8n_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.n8n_url = (n8n_url or os.getenv("N8N_URL", "http://localhost:5678")).rstrip('/')
        self.api_key = api_key or os.getenv("N8N_API_KEY")
        self.timeout = timeout
        super().__init__()
    
    def run(
        self,
        workflow_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute an n8n workflow and return the result.
        
        Args:
            workflow_id: The n8n workflow ID to execute
            input_data: Input data to pass to the workflow
            wait_for_completion: Whether to wait for workflow completion
            
        Returns:
            Workflow execution result
        """
        if not workflow_id:
            return {"error": "workflow_id is required"}
            
        try:
            # Lazy import httpx to avoid import-time overhead
            import httpx
        except ImportError:
            return {"error": "httpx not installed. Install with: pip install 'praisonai-tools[n8n]'"}
        
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-N8N-API-KEY"] = self.api_key
        
        # Execute workflow
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.n8n_url}/api/v1/workflows/{workflow_id}/execute",
                    json={"data": input_data or {}},
                    headers=headers,
                )
                response.raise_for_status()
                
                result = response.json()
                
                if wait_for_completion and result.get("executionId"):
                    # Poll for completion
                    execution_id = result["executionId"]
                    return self._wait_for_execution(client, execution_id, headers)
                
                return result
                
        except httpx.TimeoutException:
            logger.error(f"n8n workflow {workflow_id} timed out after {self.timeout}s")
            return {"error": f"Workflow execution timed out after {self.timeout} seconds"}
        except httpx.HTTPStatusError as e:
            logger.error(f"n8n API error: {e.response.status_code} - {e.response.text}")
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            logger.error(f"n8n workflow execution error: {e}")
            return {"error": str(e)}
    
    def _wait_for_execution(
        self,
        client: "httpx.Client",
        execution_id: str,
        headers: Dict[str, str],
        max_wait: int = 60,
        poll_interval: int = 2,
    ) -> Dict[str, Any]:
        """Wait for workflow execution to complete."""
        import time
        
        waited = 0
        while waited < max_wait:
            try:
                response = client.get(
                    f"{self.n8n_url}/api/v1/executions/{execution_id}",
                    headers=headers,
                )
                response.raise_for_status()
                
                execution = response.json()
                status = execution.get("status")
                
                if status in ["success", "error", "canceled"]:
                    return execution
                
                time.sleep(poll_interval)
                waited += poll_interval
                
            except Exception as e:
                logger.error(f"Error polling execution {execution_id}: {e}")
                return {"error": f"Error polling execution: {e}"}
        
        return {"error": f"Execution {execution_id} did not complete within {max_wait} seconds"}
    
    def list_workflows(self) -> Dict[str, Any]:
        """List available n8n workflows."""
        try:
            import httpx
        except ImportError:
            return {"error": "httpx not installed. Install with: pip install 'praisonai-tools[n8n]'"}
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-N8N-API-KEY"] = self.api_key
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{self.n8n_url}/api/v1/workflows",
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"n8n API error: {e.response.status_code} - {e.response.text}")
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            logger.error(f"n8n list workflows error: {e}")
            return {"error": str(e)}


@tool
def n8n_workflow(
    workflow_id: str,
    input_data: Optional[Dict[str, Any]] = None,
    n8n_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = 60.0,
    wait_for_completion: bool = True,
) -> Dict[str, Any]:
    """Execute an n8n workflow and return the result.
    
    Provides PraisonAI agents access to n8n's 400+ integrations including:
    - Communication: Slack, Discord, Telegram, Gmail, Outlook
    - Productivity: Notion, Google Sheets, Airtable, Trello
    - Databases: PostgreSQL, MongoDB, MySQL, Redis
    - APIs: REST, GraphQL, webhooks
    - And 400+ more integrations
    
    Args:
        workflow_id: The n8n workflow ID to execute
        input_data: Input data to pass to the workflow (optional)
        n8n_url: n8n instance URL (defaults to N8N_URL env var or http://localhost:5678)
        api_key: n8n API key (defaults to N8N_API_KEY env var)
        timeout: Request timeout in seconds (default: 60)
        wait_for_completion: Wait for workflow to complete (default: True)
        
    Returns:
        Dict containing workflow execution result or error information
        
    Example:
        # Send Slack message via n8n workflow
        result = n8n_workflow(
            workflow_id="slack-notify",
            input_data={
                "channel": "#general",
                "message": "Hello from PraisonAI!"
            }
        )
        
        # Create Notion page via n8n workflow
        result = n8n_workflow(
            workflow_id="notion-create-page",
            input_data={
                "title": "Meeting Notes",
                "content": "Discussion about project timeline"
            }
        )
    """
    tool = N8nWorkflowTool(
        n8n_url=n8n_url,
        api_key=api_key,
        timeout=timeout,
    )
    
    return tool.run(
        workflow_id=workflow_id,
        input_data=input_data,
        wait_for_completion=wait_for_completion,
    )


@tool
def n8n_list_workflows(
    n8n_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """List available n8n workflows.
    
    Args:
        n8n_url: n8n instance URL (defaults to N8N_URL env var or http://localhost:5678)
        api_key: n8n API key (defaults to N8N_API_KEY env var)
        
    Returns:
        Dict containing list of available workflows or error information
    """
    tool = N8nWorkflowTool(n8n_url=n8n_url, api_key=api_key)
    return tool.list_workflows()