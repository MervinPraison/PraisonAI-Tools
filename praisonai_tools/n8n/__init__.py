"""n8n Workflow Automation Tools for PraisonAI Agents.

Bidirectional integration between PraisonAI agents and n8n workflow automation platform.

Usage:
    from praisonai_tools.n8n import n8n_workflow
    
    # Agent uses n8n workflow
    result = n8n_workflow(
        workflow_id="my-workflow-id",
        input_data={"message": "Hello from PraisonAI"},
        n8n_url="http://localhost:5678",
        api_key="your-n8n-api-key"
    )
"""

from .n8n_workflow import n8n_workflow, N8nWorkflowTool

__all__ = [
    "n8n_workflow",
    "N8nWorkflowTool",
]