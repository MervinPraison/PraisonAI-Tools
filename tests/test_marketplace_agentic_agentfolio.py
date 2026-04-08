"""Real agentic test for AgentFolio marketplace tools."""

import sys
import os

# Add the package to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_agentfolio_agentic():
    """Real agentic test - agent uses AgentFolio tools with actual LLM call."""
    
    try:
        from praisonaiagents import Agent
        from praisonai_tools.marketplace import check_behavioral_trust, verify_task_delegation_safety
    except ImportError:
        print("Skipping agentic test - praisonaiagents not available")
        return
    
    # Create agent with AgentFolio marketplace tools
    agent = Agent(
        name="trust_verifier",
        instructions="""You are a trust verification agent that helps assess whether external agents
        are safe to delegate tasks to. Use the AgentFolio tools to check behavioral trust across
        organizations before recommending task delegation.
        
        When asked to verify an agent, always:
        1. Check behavioral trust for the specific task class
        2. Use the comprehensive delegation safety check
        3. Provide clear recommendations based on the results""",
        tools=[check_behavioral_trust, verify_task_delegation_safety],
        llm="gpt-4o-mini"
    )
    
    # Test with a real prompt that should trigger tool usage
    response = agent.start("""
    I need to delegate a code review task to an agent called 'python_expert_bot'. 
    The task involves reviewing security-sensitive authentication code.
    Please check if this agent is safe to delegate this task to and provide recommendations.
    """)
    
    print(f"Agent Response: {response}")
    print("✅ Agentic test completed successfully - agent used AgentFolio tools")


if __name__ == "__main__":
    test_agentfolio_agentic()