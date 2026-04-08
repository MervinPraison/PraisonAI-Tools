"""AgentFolio Tool for PraisonAI Agents.

Behavioral trust verification across organizations using SATP protocol.

Usage:
    from praisonai_tools import AgentFolioTool
    
    tool = AgentFolioTool()
    result = tool.check_behavioral_trust("agent_name", "code_review")

Environment Variables:
    AGENTFOLIO_API_KEY: AgentFolio API key (optional)
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class AgentFolioTool(BaseTool):
    """Tool for AgentFolio/SATP behavioral trust verification."""
    
    name = "agentfolio"
    description = "Check behavioral trust scores using AgentFolio/SATP protocol."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("AGENTFOLIO_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "check_behavioral_trust",
        agent_name: Optional[str] = None,
        task_class: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "check_behavioral_trust":
            return self.check_behavioral_trust(
                agent_name=agent_name,
                task_class=task_class,
                min_trust_score=kwargs.get("min_trust_score", 50.0),
                organization_filter=kwargs.get("organization_filter")
            )
        elif action == "verify_delegation_safety":
            return self.verify_delegation_safety(
                agent_name=agent_name,
                task_class=task_class,
                task_description=kwargs.get("task_description", ""),
                required_trust_level=kwargs.get("required_trust_level", 70.0)
            )
        return {"error": f"Unknown action: {action}"}
    
    def check_behavioral_trust(
        self,
        agent_name: str,
        task_class: str,
        min_trust_score: float = 50.0,
        organization_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check an agent's behavioral trust score across organizations using SATP protocol.
        
        Args:
            agent_name: Name/identifier of the agent to check
            task_class: Type of task for scoped trust (e.g., "code_review", "web_research", "data_analysis")
            min_trust_score: Minimum trust score threshold (0-100, default: 50.0)
            organization_filter: Optional filter for specific organization history
        
        Returns:
            Dictionary with behavioral trust data
        """
        if not agent_name or not task_class:
            return {
                "agent_name": agent_name or "",
                "task_class": task_class or "",
                "behavioral_score": 0.0,
                "meets_threshold": False,
                "cross_org_history": [],
                "total_tasks": 0,
                "success_rate": 0.0,
                "organizations": [],
                "reputation_trend": "unknown",
                "blockchain_verified": False,
                "error": "agent_name and task_class are required"
            }
        
        try:
            import httpx
        except ImportError:
            return {
                "agent_name": agent_name,
                "task_class": task_class,
                "behavioral_score": 0.0,
                "meets_threshold": False,
                "cross_org_history": [],
                "total_tasks": 0,
                "success_rate": 0.0,
                "organizations": [],
                "reputation_trend": "unknown",
                "blockchain_verified": False,
                "error": (
                    "httpx is required for AgentFolio/SATP integration. "
                    "Install with: pip install praisonai-tools[marketplace] or pip install httpx"
                )
            }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                params = {
                    "agent": agent_name,
                    "task_class": task_class,
                    "format": "satp"
                }
                if organization_filter:
                    params["org_filter"] = organization_filter
                if self.api_key:
                    params["api_key"] = self.api_key
                    
                response = client.get(
                    "https://api.agentfolio.io/v1/behavioral_trust",
                    params=params
                )
                response.raise_for_status()
                
                data = response.json()
                behavioral_score = data.get("behavioral_score", 0.0)
                
                return {
                    "agent_name": agent_name,
                    "task_class": task_class,
                    "behavioral_score": behavioral_score,
                    "meets_threshold": behavioral_score >= min_trust_score,
                    "cross_org_history": data.get("cross_org_history", []),
                    "total_tasks": data.get("total_tasks", 0),
                    "success_rate": data.get("success_rate", 0.0),
                    "organizations": data.get("organizations", []),
                    "reputation_trend": data.get("reputation_trend", "stable"),
                    "last_activity": data.get("last_activity"),
                    "blockchain_verified": data.get("blockchain_verified", False),
                    "satp_signature": data.get("satp_signature"),
                    "error": None
                }
                
        except httpx.RequestError as e:
            logger.error(f"AgentFolio request error: {e}")
            return {
                "agent_name": agent_name,
                "task_class": task_class,
                "behavioral_score": 0.0,
                "meets_threshold": False,
                "cross_org_history": [],
                "total_tasks": 0,
                "success_rate": 0.0,
                "organizations": [],
                "reputation_trend": "unknown",
                "blockchain_verified": False,
                "error": f"Connection error: {e}"
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"AgentFolio API error: {e.response.status_code}")
            return {
                "agent_name": agent_name,
                "task_class": task_class,
                "behavioral_score": 0.0,
                "meets_threshold": False,
                "cross_org_history": [],
                "total_tasks": 0,
                "success_rate": 0.0,
                "organizations": [],
                "reputation_trend": "unknown",
                "blockchain_verified": False,
                "error": f"API error ({e.response.status_code}): {e.response.text}"
            }
        except Exception as e:
            logger.error(f"AgentFolio unexpected error: {e}")
            return {
                "agent_name": agent_name,
                "task_class": task_class,
                "behavioral_score": 0.0,
                "meets_threshold": False,
                "cross_org_history": [],
                "total_tasks": 0,
                "success_rate": 0.0,
                "organizations": [],
                "reputation_trend": "unknown",
                "blockchain_verified": False,
                "error": f"Unexpected error: {e}"
            }
    
    def verify_delegation_safety(
        self,
        agent_name: str,
        task_class: str,
        task_description: str,
        required_trust_level: float = 70.0
    ) -> Dict[str, Any]:
        """Comprehensive safety check before delegating tasks using all trust layers."""
        behavioral_result = self.check_behavioral_trust(
            agent_name=agent_name,
            task_class=task_class,
            min_trust_score=required_trust_level
        )
        
        if behavioral_result.get("error"):
            return {
                "safe_to_delegate": False,
                "behavioral_trust": 0.0,
                "risk_assessment": "high",
                "recommendations": ["Unable to verify behavioral trust - do not delegate"],
                "verification_layers": {"behavioral": behavioral_result},
                "error": f"Behavioral trust check failed: {behavioral_result['error']}"
            }
        
        behavioral_score = behavioral_result.get("behavioral_score", 0.0)
        meets_threshold = behavioral_result.get("meets_threshold", False)
        
        if behavioral_score >= required_trust_level and meets_threshold:
            risk_level = "low"
            safe_to_delegate = True
            recommendations = ["Agent meets behavioral trust requirements"]
        elif behavioral_score >= (required_trust_level * 0.7):
            risk_level = "medium"
            safe_to_delegate = False
            recommendations = [
                "Agent has moderate behavioral trust",
                "Consider additional verification or supervision",
                "Review cross-organizational history before delegating"
            ]
        else:
            risk_level = "high"
            safe_to_delegate = False
            recommendations = [
                "Agent has insufficient behavioral trust history",
                "Do not delegate without direct supervision",
                "Consider using more trusted agents for this task type"
            ]
        
        return {
            "safe_to_delegate": safe_to_delegate,
            "behavioral_trust": behavioral_score,
            "risk_assessment": risk_level,
            "recommendations": recommendations,
            "verification_layers": {
                "behavioral": behavioral_result,
                "task_specific": {
                    "task_class": task_class,
                    "required_level": required_trust_level,
                    "meets_requirement": meets_threshold
                }
            },
            "error": None
        }


def check_behavioral_trust(
    agent_name: str,
    task_class: str,
    min_trust_score: float = 50.0,
    organization_filter: Optional[str] = None
) -> Dict[str, Any]:
    """Check an agent's behavioral trust score across organizations using SATP protocol."""
    return AgentFolioTool().check_behavioral_trust(
        agent_name=agent_name,
        task_class=task_class,
        min_trust_score=min_trust_score,
        organization_filter=organization_filter
    )


def verify_task_delegation_safety(
    agent_name: str,
    task_class: str,
    task_description: str,
    required_trust_level: float = 70.0
) -> Dict[str, Any]:
    """Comprehensive safety check before delegating tasks using all trust layers."""
    return AgentFolioTool().verify_delegation_safety(
        agent_name=agent_name,
        task_class=task_class,
        task_description=task_description,
        required_trust_level=required_trust_level
    )