#!/usr/bin/env python3
"""
Joy Trust Integration Examples for PraisonAI

This example demonstrates the native Joy Trust integration for secure agent handoffs.
"""

import os
from praisonai_tools import (
    check_trust_score, 
    verify_handoff_safety,
    trust_verified_handoff,
    is_trust_verification_enabled,
    get_trust_config,
    JoyTrustTool
)

def example_basic_trust_check():
    """Example 1: Basic trust score verification"""
    print("=== Basic Trust Score Check ===")
    
    # Check trust for a specific agent
    result = check_trust_score("researcher_agent", min_score=3.0)
    
    print(f"Agent: {result['agent_name']}")
    print(f"Trust Score: {result['trust_score']}")
    print(f"Verified: {result['verified']}")
    print(f"Meets Threshold: {result['meets_threshold']}")
    print(f"Recommendation: {result.get('recommendation', 'N/A')}")
    
    if result['error']:
        print(f"Error: {result['error']}")
    
    print()


def example_handoff_verification():
    """Example 2: Handoff safety verification"""
    print("=== Handoff Safety Verification ===")
    
    target_agent = "data_analyst"
    verification = verify_handoff_safety(target_agent, min_score=3.5)
    
    print(f"Target Agent: {verification['agent_name']}")
    print(f"Trust Score: {verification['trust_score']}")
    print(f"Handoff Safe: {verification['handoff_safe']}")
    print(f"Recommendation: {verification['recommendation']}")
    print(f"Threshold Used: {verification['threshold_used']}")
    
    if verification['handoff_safe']:
        print("✅ Safe to proceed with handoff")
    else:
        print("❌ Handoff not recommended")
    
    print()


@trust_verified_handoff(min_score=4.0)
def example_secure_delegation(agent_name: str, task: str):
    """Example 3: Decorator-based secure delegation"""
    print(f"Delegating task '{task}' to {agent_name}")
    
    # Simulate task delegation
    # In a real scenario, this would delegate to the actual agent
    return {
        "success": True,
        "result": f"Task completed by {agent_name}",
        "agent": agent_name,
        "task": task
    }


def example_environment_configuration():
    """Example 4: Environment-based configuration"""
    print("=== Environment Configuration ===")
    
    # Set environment variables for automatic trust verification
    os.environ['PRAISONAI_TRUST_PROVIDER'] = 'joy'
    os.environ['PRAISONAI_TRUST_MIN_SCORE'] = '3.5'
    os.environ['PRAISONAI_TRUST_AUTO_VERIFY'] = 'true'
    
    # Check if trust verification is enabled
    enabled = is_trust_verification_enabled()
    print(f"Trust Verification Enabled: {enabled}")
    
    # Get current configuration
    config = get_trust_config()
    print(f"Provider: {config.provider}")
    print(f"Min Score: {config.min_score}")
    print(f"Auto Verify: {config.auto_verify_handoffs}")
    print(f"Timeout: {config.timeout_seconds}s")
    
    print()


def example_advanced_configuration():
    """Example 5: Advanced tool configuration"""
    print("=== Advanced Configuration ===")
    
    # Create a custom configured tool
    trust_tool = JoyTrustTool(
        api_key=os.getenv("JOY_TRUST_API_KEY"),
        config=None  # Will use environment config
    )
    
    # Configure the tool
    config_result = trust_tool.configure(
        min_score=4.5,
        timeout_seconds=15.0,
        auto_verify_handoffs=True
    )
    
    print(f"Configuration Status: {config_result['status']}")
    print(f"Current Config: {config_result['config']}")
    
    # Use the configured tool
    result = trust_tool.check_trust("expert_agent")
    print(f"\nExpert Agent Trust: {result['trust_score']}")
    print(f"Meets Threshold: {result['meets_threshold']}")
    
    print()


def example_workflow_integration():
    """Example 6: Workflow integration pattern"""
    print("=== Workflow Integration ===")
    
    # Enable trust verification
    os.environ['PRAISONAI_TRUST_PROVIDER'] = 'joy'
    
    # Define a multi-agent workflow
    workflow_agents = [
        {"name": "data_collector", "role": "collect"},
        {"name": "data_processor", "role": "process"}, 
        {"name": "report_generator", "role": "generate"}
    ]
    
    trusted_agents = []
    
    for agent in workflow_agents:
        verification = verify_handoff_safety(agent["name"], min_score=3.0)
        
        print(f"Agent: {agent['name']}")
        print(f"  Role: {agent['role']}")
        print(f"  Trust Score: {verification['trust_score']}")
        print(f"  Safe: {verification['handoff_safe']}")
        print(f"  Recommendation: {verification['recommendation']}")
        
        if verification['handoff_safe']:
            trusted_agents.append(agent)
        
        print()
    
    print(f"Trusted agents for workflow: {len(trusted_agents)}/{len(workflow_agents)}")
    
    # Proceed with trusted agents only
    if len(trusted_agents) == len(workflow_agents):
        print("✅ All agents trusted - workflow can proceed safely")
    else:
        print("⚠️ Some agents not trusted - review workflow security")


def example_decorator_usage():
    """Example 7: Using the decorator in practice"""
    print("=== Decorator Usage ===")
    
    # Enable automatic trust verification
    os.environ['PRAISONAI_TRUST_PROVIDER'] = 'joy'
    os.environ['PRAISONAI_TRUST_AUTO_VERIFY'] = 'true'
    
    # Example with high trust requirement
    try:
        result = example_secure_delegation("trusted_expert", "analyze_data")
        print(f"Delegation Result: {result}")
    except Exception as e:
        print(f"Delegation Failed: {e}")
    
    print()


if __name__ == "__main__":
    print("Joy Trust Integration Examples\n")
    
    # Note: These examples will make actual API calls if JOY_TRUST_API_KEY is set
    # and the agents exist in the Joy Trust Network
    
    try:
        example_basic_trust_check()
        example_handoff_verification()
        example_environment_configuration()
        example_advanced_configuration()
        example_workflow_integration()
        example_decorator_usage()
        
    except Exception as e:
        print(f"Example execution error: {e}")
        print("\nNote: Some examples may fail if Joy Trust Network is not accessible")
        print("or if the example agent names don't exist in the network.")