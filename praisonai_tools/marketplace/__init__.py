"""Marketplace tools for external agent-to-agent integrations.

This module provides tools for integrating with external agent marketplaces
and trust verification services:

- Pinchwork: Task delegation to agent marketplace
- AgentID: Identity verification via ECDSA certificates  
- Joy Trust: Trust score verification before delegation

Usage:
    from praisonai_tools.marketplace import pinchwork_delegate, verify_agent_identity, check_trust_score
    from praisonaiagents import Agent
    
    agent = Agent(
        name="secure_orchestrator",
        tools=[verify_agent_identity, check_trust_score, pinchwork_delegate],
    )
"""

from praisonai_tools.marketplace.pinchwork import pinchwork_delegate
from praisonai_tools.marketplace.agentid import verify_agent_identity  
from praisonai_tools.marketplace.joy_trust import check_trust_score

__all__ = [
    "pinchwork_delegate",
    "verify_agent_identity", 
    "check_trust_score"
]