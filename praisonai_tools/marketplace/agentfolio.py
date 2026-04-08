"""AgentFolio/SATP tool for behavioral reputation across organizations."""

from typing import Dict, Any, Optional

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
def check_behavioral_trust(
    agent_name: str, 
    task_class: str, 
    min_trust_score: float = 50.0,
    organization_filter: Optional[str] = None
) -> Dict[str, Any]:
    """Check an agent's behavioral trust score across organizations using SATP protocol.
    
    AgentFolio provides task-scoped behavioral reputation that's portable across 
    organizations, unlike aggregate trust scores. An agent trusted for web research 
    isn't automatically trusted for code review.
    
    Args:
        agent_name: Name/identifier of the agent to check
        task_class: Type of task for scoped trust (e.g., "code_review", "web_research", "data_analysis")
        min_trust_score: Minimum trust score threshold (0-100, default: 50.0)
        organization_filter: Optional filter for specific organization history
    
    Returns:
        Dictionary containing:
        - agent_name: The agent identifier checked
        - task_class: The task type checked
        - behavioral_score: Task-specific behavioral score (0-100)
        - cross_org_history: History across organizations for this task type
        - meets_threshold: Boolean if score meets minimum threshold
        - total_tasks: Number of completed tasks of this type
        - success_rate: Success rate for this task type (0-1)
        - organizations: List of organizations where agent has worked
        - reputation_trend: Recent trend in behavioral scores
        - error: Error message if lookup failed
        
    Raises:
        ImportError: If httpx is not installed
    """
    try:
        import httpx
    except ImportError:
        raise ImportError(
            "httpx is required for AgentFolio/SATP integration. "
            "Install with: pip install praisonai-tools[marketplace] or pip install httpx"
        )
    
    try:
        with httpx.Client(timeout=30.0) as client:
            # Query AgentFolio/SATP API for behavioral reputation
            params = {
                "agent": agent_name,
                "task_class": task_class,
                "format": "satp"
            }
            if organization_filter:
                params["org_filter"] = organization_filter
                
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


@tool
def verify_task_delegation_safety(
    agent_name: str,
    task_class: str,
    task_description: str,
    required_trust_level: float = 70.0
) -> Dict[str, Any]:
    """Comprehensive safety check before delegating tasks using all trust layers.
    
    This tool combines AgentFolio behavioral trust with other verification methods
    to provide a complete safety assessment before task delegation.
    
    Args:
        agent_name: Name/identifier of the agent to check
        task_class: Type of task for scoped trust checking
        task_description: Specific task description for risk assessment
        required_trust_level: Required trust level for safe delegation (0-100)
    
    Returns:
        Dictionary containing:
        - safe_to_delegate: Boolean indicating if delegation is recommended
        - behavioral_trust: AgentFolio behavioral score
        - risk_assessment: Risk level (low/medium/high)
        - recommendations: List of recommended actions
        - verification_layers: Results from different trust verification systems
        - error: Error message if verification failed
    """
    try:
        import httpx
    except ImportError:
        raise ImportError(
            "httpx is required for comprehensive delegation verification. "
            "Install with: pip install praisonai-tools[marketplace] or pip install httpx"
        )
    
    # Get behavioral trust first
    behavioral_result = check_behavioral_trust(
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
    
    # Determine risk level and recommendations
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