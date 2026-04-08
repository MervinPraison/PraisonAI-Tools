"""Joy Trust Network tool for agent trust score verification."""

from typing import Dict, Any

try:
    # Try to import from praisonaiagents first (when available)
    from praisonaiagents.tools.decorator import tool
except ImportError:
    try:
        # Try praisonai_tools wrapper (when available)
        from praisonai_tools.tools.decorator import tool
    except ImportError:
        # Fallback for standalone usage
        from praisonai_tools.marketplace.decorator import tool


@tool  
def check_trust_score(agent_name: str) -> Dict[str, Any]:
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
        
    Raises:
        ImportError: If httpx is not installed
    """
    try:
        import httpx
    except ImportError:
        raise ImportError(
            "httpx is required for Joy Trust Network integration. "
            "Install with: pip install praisonai-tools[marketplace] or pip install httpx"
        )
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                "https://joy-connect.fly.dev/agents/discover",
                params={"name": agent_name}
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
        return {
            "agent_name": agent_name,
            "trust_score": 0.0,
            "verified": False,
            "reputation": {},
            "recommendations": 0,
            "error": f"Connection error: {e}"
        }
    except httpx.HTTPStatusError as e:
        return {
            "agent_name": agent_name,
            "trust_score": 0.0,
            "verified": False,
            "reputation": {},
            "recommendations": 0,
            "error": f"API error ({e.response.status_code}): {e.response.text}"
        }
    except Exception as e:
        return {
            "agent_name": agent_name,
            "trust_score": 0.0,
            "verified": False,
            "reputation": {},
            "recommendations": 0,
            "error": f"Unexpected error: {e}"
        }