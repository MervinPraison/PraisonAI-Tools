"""Joy Trust Tool for PraisonAI Agents.

Agent trust score verification using Joy Trust Network.

Usage:
    from praisonai_tools import JoyTrustTool
    
    tool = JoyTrustTool()
    result = tool.check_trust("agent_name")

Environment Variables:
    JOY_TRUST_API_KEY: Joy Trust API key (optional)
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class JoyTrustTool(BaseTool):
    """Tool for Joy Trust Network verification."""
    
    name = "joy_trust"
    description = "Check agent trust scores using Joy Trust Network."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("JOY_TRUST_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "check_trust",
        agent_name: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "check_trust":
            return self.check_trust(agent_name=agent_name)
        return {"error": f"Unknown action: {action}"}
    
    def check_trust(self, agent_name: str) -> Dict[str, Any]:
        """Check an agent's trust score on Joy Trust Network before delegation.
        
        Args:
            agent_name: Name/identifier of the agent to check
        
        Returns:
            Dictionary containing:
            - trust_score: Numeric trust score (0-1)
            - verified: Boolean indicating if agent is verified
            - reputation: Reputation metrics if available
            - recommendations: Number of positive recommendations
            - error: Error message if lookup failed
        """
        if not agent_name:
            return {
                "agent_name": "",
                "trust_score": 0.0,
                "verified": False,
                "reputation": {},
                "recommendations": 0,
                "error": "agent_name is required"
            }
        
        try:
            import httpx
        except ImportError:
            return {
                "agent_name": agent_name,
                "trust_score": 0.0,
                "verified": False,
                "reputation": {},
                "recommendations": 0,
                "error": (
                    "httpx is required for Joy Trust Network integration. "
                    "Install with: pip install praisonai-tools[marketplace] or pip install httpx"
                )
            }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                params = {"name": agent_name}
                if self.api_key:
                    params["api_key"] = self.api_key
                    
                response = client.get(
                    "https://joy-connect.fly.dev/agents/discover",
                    params=params
                )
                response.raise_for_status()
                
                data = response.json()
                
                return {
                    "agent_name": agent_name,
                    "trust_score": data.get("trust_score", 0.0),
                    "verified": data.get("verified", False),
                    "reputation": data.get("reputation", {}),
                    "recommendations": data.get("recommendations", 0),
                    "last_activity": data.get("last_activity"),
                    "network_rank": data.get("network_rank"),
                    "error": None
                }
                
        except httpx.RequestError as e:
            logger.error(f"Joy Trust request error: {e}")
            return {
                "agent_name": agent_name,
                "trust_score": 0.0,
                "verified": False,
                "reputation": {},
                "recommendations": 0,
                "error": f"Connection error: {e}"
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Joy Trust API error: {e.response.status_code}")
            return {
                "agent_name": agent_name,
                "trust_score": 0.0,
                "verified": False,
                "reputation": {},
                "recommendations": 0,
                "error": f"API error ({e.response.status_code}): {e.response.text}"
            }
        except Exception as e:
            logger.error(f"Joy Trust unexpected error: {e}")
            return {
                "agent_name": agent_name,
                "trust_score": 0.0,
                "verified": False,
                "reputation": {},
                "recommendations": 0,
                "error": f"Unexpected error: {e}"
            }


def check_trust_score(agent_name: str) -> Dict[str, Any]:
    """Check an agent's trust score on Joy Trust Network before delegation."""
    return JoyTrustTool().check_trust(agent_name=agent_name)