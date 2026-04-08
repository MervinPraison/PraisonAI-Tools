"""Pinchwork marketplace tool for task delegation."""

from typing import List, Optional

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
def pinchwork_delegate(task: str, skills_required: Optional[List[str]] = None, budget: float = 0.0) -> str:
    """Delegate a task to the Pinchwork agent marketplace.
    
    Args:
        task: Description of the task to delegate
        skills_required: List of required skills for the agent (optional)
        budget: Maximum budget for the task (default: 0.0)
    
    Returns:
        Result from the marketplace agent that completed the task
        
    Raises:
        ImportError: If httpx is not installed
        ConnectionError: If unable to reach Pinchwork API
    """
    try:
        import httpx
    except ImportError:
        raise ImportError(
            "httpx is required for Pinchwork integration. "
            "Install with: pip install praisonai-tools[marketplace] or pip install httpx"
        )
    
    try:
        # POST to Pinchwork API
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
    except httpx.HTTPStatusError as e:
        return f"Pinchwork API error ({e.response.status_code}): {e.response.text}"
    except Exception as e:
        return f"Unexpected error during task delegation: {e}"