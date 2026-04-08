"""AgentID tool for agent identity verification via ECDSA certificates."""

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
def verify_agent_identity(agent_url: str) -> Dict[str, Any]:
    """Verify an external agent's identity using AgentID certificates.
    
    Args:
        agent_url: URL of the agent to verify
    
    Returns:
        Dictionary with verification result containing:
        - verified: Boolean indicating if agent is verified
        - trust_score: Numeric trust score (0-1) 
        - certificate: Certificate details if verified
        - error: Error message if verification failed
        
    Raises:
        ImportError: If httpx is not installed
    """
    try:
        import httpx
    except ImportError:
        raise ImportError(
            "httpx is required for AgentID verification. "
            "Install with: pip install praisonai-tools[marketplace] or pip install httpx"
        )
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                "https://getagentid.dev/api/verify",
                params={"agent": agent_url}
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
        return {
            "verified": False,
            "trust_score": 0.0,
            "certificate": {},
            "agent_url": agent_url,
            "error": f"Connection error: {e}"
        }
    except httpx.HTTPStatusError as e:
        return {
            "verified": False,
            "trust_score": 0.0,
            "certificate": {},
            "agent_url": agent_url,
            "error": f"API error ({e.response.status_code}): {e.response.text}"
        }
    except Exception as e:
        return {
            "verified": False,
            "trust_score": 0.0,
            "certificate": {},
            "agent_url": agent_url,
            "error": f"Unexpected error: {e}"
        }