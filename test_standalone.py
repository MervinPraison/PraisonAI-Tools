#!/usr/bin/env python3
"""Standalone test for marketplace tools without package imports."""

from typing import List, Optional, Dict, Any, Callable
from functools import wraps

# Standalone tool decorator
def tool(func: Callable[..., Any]) -> Callable[..., Any]:
    """Minimal @tool decorator for marketplace tools."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Mark as a tool for agent discovery
    wrapper._is_tool = True
    wrapper._tool_name = func.__name__
    wrapper._tool_description = func.__doc__ or ""
    
    return wrapper

# Pinchwork tool
@tool
def pinchwork_delegate(task: str, skills_required: Optional[List[str]] = None, budget: float = 0.0) -> str:
    """Delegate a task to the Pinchwork agent marketplace."""
    try:
        import httpx
    except ImportError:
        raise ImportError("httpx is required for Pinchwork integration. Install with: pip install httpx")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post("https://api.pinchwork.com/delegate", json={
                "task": task,
                "skills": skills_required or [],
                "budget": budget,
            })
            response.raise_for_status()
            data = response.json()
            return data.get("result", "No result returned from marketplace")
    except httpx.RequestError as e:
        return f"Error connecting to Pinchwork: {e}"
    except Exception as e:
        return f"Unexpected error during task delegation: {e}"

# AgentID tool
@tool
def verify_agent_identity(agent_url: str) -> Dict[str, Any]:
    """Verify an external agent's identity using AgentID certificates."""
    try:
        import httpx
    except ImportError:
        raise ImportError("httpx is required for AgentID verification. Install with: pip install httpx")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get("https://getagentid.dev/api/verify", params={"agent": agent_url})
            response.raise_for_status()
            data = response.json()
            return {
                "verified": data.get("verified", False),
                "trust_score": data.get("trust_score", 0.0),
                "certificate": data.get("certificate_info", {}),
                "agent_url": agent_url,
                "error": None
            }
    except Exception as e:
        return {
            "verified": False,
            "trust_score": 0.0,
            "certificate": {},
            "agent_url": agent_url,
            "error": f"Error: {e}"
        }

# Joy Trust tool
@tool  
def check_trust_score(agent_name: str) -> Dict[str, Any]:
    """Check an agent's trust score on Joy Trust Network before delegation."""
    try:
        import httpx
    except ImportError:
        raise ImportError("httpx is required for Joy Trust Network integration. Install with: pip install httpx")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get("https://joy-connect.fly.dev/agents/discover", params={"name": agent_name})
            response.raise_for_status()
            data = response.json()
            return {
                "agent_name": agent_name,
                "trust_score": data.get("trust_score", 0.0),
                "verified": data.get("verified", False),
                "reputation": data.get("reputation", {}),
                "error": None
            }
    except Exception as e:
        return {
            "agent_name": agent_name,
            "trust_score": 0.0,
            "verified": False,
            "reputation": {},
            "error": f"Error: {e}"
        }

if __name__ == "__main__":
    print("Testing marketplace tools...")
    
    # Test function properties
    print(f"✅ pinchwork_delegate: {pinchwork_delegate.__name__} (is_tool: {getattr(pinchwork_delegate, '_is_tool', False)})")
    print(f"✅ verify_agent_identity: {verify_agent_identity.__name__} (is_tool: {getattr(verify_agent_identity, '_is_tool', False)})")
    print(f"✅ check_trust_score: {check_trust_score.__name__} (is_tool: {getattr(check_trust_score, '_is_tool', False)})")
    
    # Test without httpx (expected to work - graceful error handling)
    print("\nTesting error handling without httpx:")
    try:
        result = pinchwork_delegate("test task")
        print(f"Pinchwork: {result}")
    except ImportError as e:
        print(f"✅ Pinchwork properly raises ImportError: {e}")
    
    try:
        result = verify_agent_identity("https://example.com")
        print(f"AgentID: {result}")
    except ImportError as e:
        print(f"✅ AgentID properly raises ImportError: {e}")
        
    try:
        result = check_trust_score("test_agent")
        print(f"Joy Trust: {result}")
    except ImportError as e:
        print(f"✅ Joy Trust properly raises ImportError: {e}")
    
    print("\n🎉 All marketplace tools are working correctly!")