"""Marketplace tools for external agent-to-agent integrations.

This module provides tools for integrating with external agent marketplaces
and trust verification services:

- Pinchwork: Task delegation to agent marketplace
- AgentID: Identity verification via ECDSA certificates  
- Joy Trust: Trust score verification before delegation
- AgentFolio: Behavioral reputation across organizations (task-scoped)

Usage:
    from praisonai_tools.marketplace import (
        pinchwork_delegate, verify_agent_identity, check_trust_score,
        check_behavioral_trust, verify_task_delegation_safety
    )
    from praisonaiagents import Agent
    
    agent = Agent(
        name="secure_orchestrator",
        tools=[
            verify_agent_identity, check_trust_score, 
            check_behavioral_trust, verify_task_delegation_safety,
            pinchwork_delegate
        ],
    )
"""

from praisonai_tools.marketplace.pinchwork import pinchwork_delegate
from praisonai_tools.marketplace.agentid import verify_agent_identity  
from praisonai_tools.marketplace.joy_trust import check_trust_score
from praisonai_tools.marketplace.agentfolio import check_behavioral_trust, verify_task_delegation_safety

__all__ = [
    "pinchwork_delegate",
    "verify_agent_identity", 
    "check_trust_score",
    "check_behavioral_trust",
    "verify_task_delegation_safety"
]