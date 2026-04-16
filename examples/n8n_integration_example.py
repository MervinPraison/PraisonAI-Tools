"""n8n Integration Example for PraisonAI Agents.

This example demonstrates how to use the n8n integration tools to enable
PraisonAI agents to access n8n's 400+ integrations (Slack, Gmail, Notion, etc.).

Prerequisites:
1. Install PraisonAI Tools with n8n support:
   pip install "praisonai-tools[n8n]"

2. Set up n8n (local or cloud):
   - Local: docker run -it --rm --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
   - Cloud: https://n8n.cloud

3. Configure environment variables:
   export N8N_URL="http://localhost:5678"  # or your n8n instance URL
   export N8N_API_KEY="your-api-key"       # optional for local testing

4. Create some workflows in n8n that your agents can use

Usage:
    python examples/n8n_integration_example.py
"""

import os
from praisonaiagents import Agent
from praisonai_tools.n8n import n8n_workflow, n8n_list_workflows


def example_list_workflows():
    """Example: List available n8n workflows."""
    print("🔍 Listing available n8n workflows...")
    
    try:
        result = n8n_list_workflows()
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return
        
        workflows = result.get("data", [])
        if workflows:
            print(f"✅ Found {len(workflows)} workflows:")
            for workflow in workflows[:5]:  # Show first 5
                print(f"  - {workflow.get('name', 'Unnamed')} (ID: {workflow.get('id')})")
        else:
            print("📝 No workflows found. Create some workflows in n8n first!")
        
        return workflows
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        return []


def example_execute_workflow():
    """Example: Execute a simple n8n workflow."""
    print("\n🚀 Executing n8n workflow...")
    
    # This would be the ID of a workflow you created in n8n
    # For demo purposes, we'll use a placeholder
    workflow_id = os.getenv("N8N_TEST_WORKFLOW_ID", "demo-workflow-123")
    
    try:
        result = n8n_workflow(
            workflow_id=workflow_id,
            input_data={
                "message": "Hello from PraisonAI!",
                "timestamp": "2026-04-16T12:00:00Z",
                "source": "praisonai-agent"
            },
            wait_for_completion=True
        )
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            if "workflow" in result["error"].lower():
                print("💡 Tip: Create a test workflow in n8n and set N8N_TEST_WORKFLOW_ID")
            return
        
        print("✅ Workflow executed successfully!")
        print(f"📊 Result: {result}")
        
    except Exception as e:
        print(f"❌ Exception: {e}")


def example_agent_with_n8n_tools():
    """Example: PraisonAI agent using n8n tools."""
    print("\n🤖 Creating PraisonAI agent with n8n tools...")
    
    # Create an agent with n8n tools
    agent = Agent(
        name="automation-agent",
        instructions="""
        You are an automation assistant with access to n8n workflows.
        You can help users automate tasks using n8n's 400+ integrations.
        
        Available capabilities through n8n:
        - Send messages to Slack, Discord, Telegram
        - Create pages in Notion, Google Docs
        - Add rows to Google Sheets, Airtable
        - Send emails via Gmail, Outlook
        - Create tasks in Trello, Jira, Linear
        - Store data in databases (PostgreSQL, MongoDB, etc.)
        - Call external APIs and webhooks
        
        Always explain what you're doing and ask for workflow IDs when needed.
        """,
        tools=[n8n_workflow, n8n_list_workflows],
        llm="gpt-4o-mini",  # Use a lightweight model for demo
    )
    
    print("✅ Agent created with n8n tools!")
    return agent


def example_agent_conversation():
    """Example conversation with the n8n-enabled agent."""
    agent = example_agent_with_n8n_tools()
    
    if not agent:
        print("❌ Failed to create agent")
        return
    
    print("\n💬 Starting conversation with agent...")
    
    # Example conversation
    conversations = [
        "Can you list the available n8n workflows?",
        "What can you help me automate using n8n?",
        # "Execute the Slack notification workflow with the message 'Test from PraisonAI'"
    ]
    
    for i, message in enumerate(conversations, 1):
        print(f"\n👤 User #{i}: {message}")
        try:
            response = agent.start(message)
            print(f"🤖 Agent: {response}")
        except Exception as e:
            print(f"❌ Error in conversation: {e}")


def main():
    """Main function to run all examples."""
    print("🔗 n8n Integration Example for PraisonAI Agents")
    print("=" * 50)
    
    # Check configuration
    n8n_url = os.getenv("N8N_URL", "http://localhost:5678")
    n8n_api_key = os.getenv("N8N_API_KEY")
    
    print(f"🔧 Configuration:")
    print(f"   N8N_URL: {n8n_url}")
    print(f"   N8N_API_KEY: {'Set' if n8n_api_key else 'Not set (OK for local testing)'}")
    
    # Run examples
    workflows = example_list_workflows()
    
    if workflows:
        example_execute_workflow()
    else:
        print("\n💡 To test workflow execution:")
        print("   1. Open your n8n instance and create a simple workflow")
        print("   2. Set the workflow ID: export N8N_TEST_WORKFLOW_ID='your-workflow-id'")
        print("   3. Run this example again")
    
    # Agent examples (these work even without actual workflows)
    try:
        example_agent_conversation()
    except Exception as e:
        print(f"❌ Agent example failed: {e}")
        print("💡 This might be due to missing OpenAI API key or n8n connectivity")
    
    print("\n✨ Example completed!")
    print("\n📚 Next steps:")
    print("   - Create workflows in your n8n instance")
    print("   - Use the agent in your own applications")
    print("   - Explore n8n's 400+ integrations at https://n8n.io/integrations")


if __name__ == "__main__":
    main()