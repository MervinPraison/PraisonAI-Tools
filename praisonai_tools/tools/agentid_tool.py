"""AgentID Tool for PraisonAI Agents.

Agent identity verification using ECDSA certificates.

Usage:
    from praisonai_tools import AgentIDTool
    
    tool = AgentIDTool()
    result = tool.verify("https://agent.example.com")

Environment Variables:
    AGENTID_API_KEY: AgentID API key (optional)
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class AgentIDTool(BaseTool):
    """Tool for AgentID agent verification."""
    
    name = "agentid"
    description = "Verify agent identity using AgentID certificates."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("AGENTID_API_KEY")
        super().__init__()
    
    def run(
        self,
        action: str = "verify",
        agent_url: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "verify":
            return self.verify(agent_url=agent_url)
        return {"error": f"Unknown action: {action}"}
    
    def verify(self, agent_url: str) -> Dict[str, Any]:
        """Verify an external agent's identity using AgentID certificates.
        
        Args:
            agent_url: URL of the agent to verify
        
        Returns:
            Dictionary with verification result containing:
            - verified: Boolean indicating if agent is verified
            - trust_score: Numeric trust score (0-1) 
            - certificate: Certificate details if verified
            - error: Error message if verification failed
        """
        if not agent_url:
            return {
                "verified": False,
                "trust_score": 0.0,
                "certificate": {},
                "agent_url": "",
                "error": "agent_url is required"
            }
        
        try:
            import httpx
        except ImportError:
            return {
                "verified": False,
                "trust_score": 0.0,
                "certificate": {},
                "agent_url": agent_url,
                "error": (
                    "httpx is required for AgentID verification. "
                    "Install with: pip install praisonai-tools[marketplace] or pip install httpx"
                )
            }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                params = {"agent": agent_url}
                if self.api_key:
                    params["api_key"] = self.api_key
                    
                response = client.get(
                    "https://getagentid.dev/api/verify",
                    params=params
                )
                response.raise_for_status()
                
                data = response.json()
                
                return {
                    "verified": data.get("verified", False),
                    "trust_score": data.get("trust_score", 0.0),
                    "certificate": data.get("certificate_info", {}),
                    "agent_url": agent_url,
                    "timestamp": data.get("timestamp"),
                    "error": None
                }
                
        except httpx.RequestError as e:
            logger.error(f"AgentID request error: {e}")
            return {
                "verified": False,
                "trust_score": 0.0,
                "certificate": {},
                "agent_url": agent_url,
                "error": f"Connection error: {e}"
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"AgentID API error: {e.response.status_code}")
            return {
                "verified": False,
                "trust_score": 0.0,
                "certificate": {},
                "agent_url": agent_url,
                "error": f"API error ({e.response.status_code}): {e.response.text}"
            }
        except Exception as e:
            logger.error(f"AgentID unexpected error: {e}")
            return {
                "verified": False,
                "trust_score": 0.0,
                "certificate": {},
                "agent_url": agent_url,
                "error": f"Unexpected error: {e}"
            }


def verify_agent_identity(agent_url: str) -> Dict[str, Any]:
    """Verify an external agent's identity using AgentID certificates."""
    return AgentIDTool().verify(agent_url=agent_url)