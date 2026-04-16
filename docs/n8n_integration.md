# n8n Integration for PraisonAI Agents

Enable bidirectional integration between PraisonAI agents and n8n workflow automation platform, providing access to **400+ integrations** including Slack, Gmail, Notion, databases, APIs, and more.

## Overview

The n8n integration allows:

- **PraisonAI → n8n**: Agents can execute n8n workflows to access 400+ integrations
- **n8n → PraisonAI**: n8n workflows can invoke PraisonAI agents (see API endpoint section)

## Installation

```bash
# Install with n8n support
pip install "praisonai-tools[n8n]"
```

## Setup

### 1. n8n Instance

**Local Development:**
```bash
# Run n8n locally with Docker
docker run -it --rm --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```

**Production:**
- Use [n8n Cloud](https://n8n.cloud) (recommended)
- Or self-host n8n on your infrastructure

### 2. Environment Variables

```bash
export N8N_URL="http://localhost:5678"  # Your n8n instance URL
export N8N_API_KEY="your-api-key"       # Optional for local, required for production
```

### 3. Create API Key (Production)

1. Open n8n instance
2. Go to Settings → API
3. Generate new API key
4. Set `N8N_API_KEY` environment variable

## Quick Start

### Basic Usage

```python
from praisonai_tools.n8n import n8n_workflow, n8n_list_workflows

# List available workflows
workflows = n8n_list_workflows()
print(f"Available workflows: {len(workflows.get('data', []))}")

# Execute a workflow
result = n8n_workflow(
    workflow_id="your-workflow-id",
    input_data={"message": "Hello from PraisonAI!"}
)
```

### With PraisonAI Agents

```python
from praisonaiagents import Agent
from praisonai_tools.n8n import n8n_workflow, n8n_list_workflows

# Create agent with n8n tools
agent = Agent(
    name="automation-agent",
    instructions="You help automate tasks using n8n workflows with 400+ integrations",
    tools=[n8n_workflow, n8n_list_workflows],
)

# Agent can now use n8n workflows
response = agent.start("Send a Slack message to #general saying 'Hello team!'")
```

## Available Tools

### `n8n_workflow`

Execute an n8n workflow and return the result.

**Parameters:**
- `workflow_id` (str): The n8n workflow ID to execute
- `input_data` (dict, optional): Input data to pass to the workflow
- `n8n_url` (str, optional): n8n instance URL (defaults to `N8N_URL` env var)
- `api_key` (str, optional): n8n API key (defaults to `N8N_API_KEY` env var)
- `timeout` (float, optional): Request timeout in seconds (default: 60)
- `wait_for_completion` (bool, optional): Wait for workflow completion (default: True)

**Returns:** Dict with execution result or error information

**Example:**
```python
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
```

### `n8n_list_workflows`

List available n8n workflows.

**Parameters:**
- `n8n_url` (str, optional): n8n instance URL
- `api_key` (str, optional): n8n API key

**Returns:** Dict containing list of workflows or error information

**Example:**
```python
workflows = n8n_list_workflows()
for workflow in workflows.get("data", []):
    print(f"- {workflow['name']} (ID: {workflow['id']})")
```

## Common Use Cases

### 1. Communication Automation

```python
# Slack notifications
n8n_workflow("slack-notify", {
    "channel": "#alerts",
    "message": "Task completed successfully!",
    "emoji": ":white_check_mark:"
})

# Email with Gmail
n8n_workflow("gmail-send", {
    "to": "user@example.com",
    "subject": "Report Ready",
    "body": "Your daily report is attached."
})
```

### 2. Data Management

```python
# Add to Google Sheets
n8n_workflow("sheets-append", {
    "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
    "range": "Sheet1!A1:E1",
    "values": [["Date", "Name", "Status", "Notes"]]
})

# Create Notion page
n8n_workflow("notion-create", {
    "database_id": "your-database-id",
    "properties": {
        "Title": {"title": [{"text": {"content": "New Task"}}]},
        "Status": {"select": {"name": "To Do"}}
    }
})
```

### 3. Task Management

```python
# Create Jira ticket
n8n_workflow("jira-create-issue", {
    "project": "PROJ",
    "summary": "Bug report from agent",
    "description": "Issue details...",
    "issue_type": "Bug"
})

# Add Trello card
n8n_workflow("trello-add-card", {
    "list_id": "your-list-id",
    "name": "New Task",
    "desc": "Task description"
})
```

## Agent Examples

### Multi-Platform Notification Agent

```python
agent = Agent(
    name="notifier",
    instructions="""
    You send notifications across multiple platforms using n8n workflows.
    Available workflows:
    - slack-notify: Send Slack messages
    - discord-webhook: Send Discord messages  
    - email-send: Send emails
    - teams-notify: Send Microsoft Teams messages
    
    Always ask which platform and customize the message appropriately.
    """,
    tools=[n8n_workflow, n8n_list_workflows]
)
```

### Data Sync Agent

```python
agent = Agent(
    name="data-sync",
    instructions="""
    You help synchronize data between different systems using n8n.
    You can:
    - Sync data between databases
    - Update spreadsheets
    - Create/update CRM records
    - Generate reports
    
    Always confirm the source and destination before proceeding.
    """,
    tools=[n8n_workflow]
)
```

## Error Handling

The n8n tools provide detailed error information:

```python
result = n8n_workflow("invalid-workflow")

if "error" in result:
    print(f"Error: {result['error']}")
    # Common errors:
    # - "workflow_id is required"
    # - "httpx not installed. Install with: pip install 'praisonai-tools[n8n]'"
    # - "HTTP 404: Workflow not found"
    # - "Workflow execution timed out after 60 seconds"
```

## Configuration

### Timeout Settings

```python
# Short timeout for quick workflows
result = n8n_workflow(
    workflow_id="quick-task",
    timeout=10.0
)

# Long timeout for complex workflows
result = n8n_workflow(
    workflow_id="data-processing",
    timeout=300.0  # 5 minutes
)
```

### Async vs Sync Execution

```python
# Wait for completion (default)
result = n8n_workflow("workflow-id", wait_for_completion=True)

# Fire-and-forget
result = n8n_workflow("workflow-id", wait_for_completion=False)
# Returns immediately with executionId
```

## Integration with n8n → PraisonAI

To enable n8n workflows to invoke PraisonAI agents, add this endpoint to your PraisonAI application:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from praisonaiagents import Agent

app = FastAPI()

class InvokeRequest(BaseModel):
    agent_name: str
    message: str
    session_id: str = None

@app.post("/api/v1/agents/{agent_id}/invoke")
async def invoke_agent(agent_id: str, request: InvokeRequest):
    """Endpoint for n8n to invoke PraisonAI agents."""
    # Load your agent
    agent = get_agent(agent_id)  # Your agent loading logic
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    
    result = await agent.astart(request.message)
    return {"result": result, "session_id": request.session_id or "default"}
```

Then use n8n's HTTP Request node to call this endpoint.

## Best Practices

### 1. Workflow Design
- Create focused workflows for specific tasks
- Use descriptive workflow names and IDs
- Add error handling in your n8n workflows
- Test workflows manually before using with agents

### 2. Security
- Use API keys for production environments
- Implement input validation in n8n workflows
- Consider rate limiting for agent-triggered workflows
- Audit workflow executions regularly

### 3. Performance
- Use appropriate timeouts based on workflow complexity
- Consider async execution for long-running workflows
- Monitor n8n instance performance
- Cache workflow lists when possible

### 4. Error Handling
- Always check for error responses
- Implement retry logic for transient failures
- Log workflow execution results
- Provide fallback options when workflows fail

## Troubleshooting

### Common Issues

**Connection Errors:**
```python
# Check n8n connectivity
result = n8n_list_workflows()
if "error" in result:
    print("n8n connection issue:", result["error"])
```

**Workflow Not Found:**
```python
# Verify workflow exists
workflows = n8n_list_workflows()
workflow_ids = [w["id"] for w in workflows.get("data", [])]
print("Available workflows:", workflow_ids)
```

**Authentication Issues:**
```python
# Check API key configuration
import os
api_key = os.getenv("N8N_API_KEY")
if not api_key:
    print("N8N_API_KEY not set - OK for local testing")
else:
    print("API key configured")
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now n8n tool calls will show detailed logs
result = n8n_workflow("test-workflow")
```

## Resources

- [n8n Documentation](https://docs.n8n.io/)
- [n8n API Reference](https://docs.n8n.io/api/)
- [n8n Workflow Templates](https://n8n.io/workflows)
- [n8n Integrations](https://n8n.io/integrations)
- [PraisonAI Documentation](https://docs.praison.ai)

## Contributing

To contribute to the n8n integration:

1. Fork the [PraisonAI-Tools repository](https://github.com/MervinPraison/PraisonAI-Tools)
2. Create your feature branch
3. Add tests for your changes
4. Update documentation
5. Submit a pull request

## License

This integration is released under the MIT License, same as PraisonAI Tools.