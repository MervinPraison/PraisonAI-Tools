"""Joy Trust Tool for PraisonAI Agents.

Enhanced agent trust score verification using Joy Trust Network with native
integration for secure agent handoffs.

Features:
- Basic trust score verification
- Automatic handoff trust verification
- Environment variable configuration
- Decorator for trust-aware agent delegation
- Integration hooks for PraisonAI handoff system

Usage:
    Basic usage:
        from praisonai_tools import check_trust_score
        result = check_trust_score("agent_name")
    
    Advanced usage with handoff integration:
        from praisonai_tools import JoyTrustTool, trust_verified_handoff
        
        # Enable automatic trust verification
        os.environ['PRAISONAI_TRUST_PROVIDER'] = 'joy'
        
        @trust_verified_handoff(min_score=3.0)
        def delegate_to_agent(agent, task):
            return agent.run(task)

Environment Variables:
    JOY_TRUST_API_KEY: Joy Trust API key (optional)
    PRAISONAI_TRUST_PROVIDER: Set to 'joy' to enable automatic trust verification
    PRAISONAI_TRUST_MIN_SCORE: Minimum trust score threshold (default: 3.0)
    PRAISONAI_TRUST_AUTO_VERIFY: Enable automatic handoff verification (default: true)
"""

import os
import logging
import time
from typing import Any, Dict, Optional, Union, Callable, List
from dataclasses import dataclass
from functools import wraps

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


@dataclass
class TrustConfig:
    """Configuration for Joy Trust integration."""
    
    enabled: bool = False
    provider: str = "joy"
    min_score: float = 3.0
    auto_verify_handoffs: bool = True
    timeout_seconds: float = 10.0
    cache_duration: int = 300  # 5 minutes
    fallback_on_error: bool = True
    
    @classmethod
    def from_env(cls) -> 'TrustConfig':
        """Create configuration from environment variables."""
        return cls(
            enabled=os.getenv('PRAISONAI_TRUST_PROVIDER', '').lower() == 'joy',
            provider=os.getenv('PRAISONAI_TRUST_PROVIDER', 'joy'),
            min_score=float(os.getenv('PRAISONAI_TRUST_MIN_SCORE', '3.0')),
            auto_verify_handoffs=os.getenv('PRAISONAI_TRUST_AUTO_VERIFY', 'true').lower() == 'true',
            timeout_seconds=float(os.getenv('PRAISONAI_TRUST_TIMEOUT', '10.0')),
            cache_duration=int(os.getenv('PRAISONAI_TRUST_CACHE_DURATION', '300')),
            fallback_on_error=os.getenv('PRAISONAI_TRUST_FALLBACK', 'true').lower() == 'true'
        )


class JoyTrustTool(BaseTool):
    """Enhanced tool for Joy Trust Network verification with native integration."""
    
    name = "joy_trust"
    description = "Check agent trust scores using Joy Trust Network with automatic handoff integration."
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[TrustConfig] = None):
        self.api_key = api_key or os.getenv("JOY_TRUST_API_KEY")
        self.config = config or TrustConfig.from_env()
        self._cache = {}  # Simple in-memory cache
        super().__init__()
    
    def run(
        self,
        action: str = "check_trust",
        agent_name: Optional[str] = None,
        min_score: Optional[float] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """Run trust verification action."""
        if action == "check_trust":
            return self.check_trust(agent_name=agent_name, min_score=min_score)
        elif action == "verify_handoff":
            return self.verify_handoff_safety(agent_name=agent_name, min_score=min_score)
        elif action == "configure":
            return self.configure(**kwargs)
        return {"error": f"Unknown action: {action}"}
    
    def check_trust(self, agent_name: str, min_score: Optional[float] = None) -> Dict[str, Any]:
        """Check an agent's trust score on Joy Trust Network.
        
        Args:
            agent_name: Name/identifier of the agent to check
            min_score: Minimum acceptable trust score (uses config default if not provided)
        
        Returns:
            Dictionary containing trust information and verification status
        """
        if not agent_name:
            return {
                "agent_name": "",
                "agent_id": None,
                "trust_score": 0.0,
                "verified": False,
                "meets_threshold": False,
                "threshold_used": 0.0,
                "vouch_count": 0,
                "capabilities": [],
                "tier": None,
                "badges": [],
                "error": "agent_name is required"
            }
        
        min_threshold = min_score if min_score is not None else self.config.min_score
        
        # Check cache first
        cache_key = f"{agent_name}_{min_threshold}"
        if cache_key in self._cache:
            cached_result = self._cache[cache_key]
            if cached_result.get('_cached_at', 0) + self.config.cache_duration > time.time():
                logger.debug(f"Using cached trust score for {agent_name}")
                return cached_result
        
        try:
            import httpx
        except ImportError:
            return {
                "agent_name": agent_name,
                "agent_id": None,
                "trust_score": 0.0,
                "verified": False,
                "meets_threshold": False,
                "threshold_used": min_threshold,
                "vouch_count": 0,
                "capabilities": [],
                "tier": None,
                "badges": [],
                "error": (
                    "httpx is required for Joy Trust Network integration. "
                    "Install with: pip install praisonai-tools[marketplace] or pip install httpx"
                )
            }
        
        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                headers = {}
                if self.api_key:
                    headers["x-api-key"] = self.api_key

                response = client.get(
                    "https://joy-connect.fly.dev/agents/discover",
                    params={"query": agent_name},
                    headers=headers
                )
                response.raise_for_status()

                data = response.json()

                # FIX: Extract agent from the agents array, not top level
                # Use 'or' to handle both missing key AND null value
                agents = data.get("agents") or []

                # Find matching agent by name (case-insensitive, exact match only)
                # Security: Do NOT fallback to first result - could return wrong agent's trust
                agent = next((a for a in agents if a.get("name", "").lower() == agent_name.lower()), None)

                if not agent:
                    return {
                        "agent_name": agent_name,
                        "agent_id": None,
                        "trust_score": 0.0,
                        "verified": False,
                        "meets_threshold": False,
                        "threshold_used": min_threshold,
                        "vouch_count": 0,
                        "capabilities": [],
                        "tier": None,
                        "badges": [],
                        "error": f"Agent '{agent_name}' not found on Joy Trust Network"
                    }

                # Read from the agent object, not top level
                # Use 'or' to handle both missing key AND null value
                trust_score = agent.get("trust_score") or 0.0

                result = {
                    "agent_name": agent.get("name", agent_name),
                    "agent_id": agent.get("id"),
                    "trust_score": trust_score,
                    "verified": agent.get("verified", False),
                    "meets_threshold": trust_score >= min_threshold,
                    "threshold_used": min_threshold,
                    "vouch_count": agent.get("vouch_count", 0),
                    "capabilities": agent.get("capabilities", []),
                    "tier": agent.get("tier", "free"),
                    "badges": agent.get("badges", []),
                    "error": None,
                    "_cached_at": time.time()
                }

                # Cache the result
                self._cache[cache_key] = result

                return result
                
        except httpx.RequestError as e:
            logger.error(f"Joy Trust request error: {e}")
            return {
                "agent_name": agent_name,
                "agent_id": None,
                "trust_score": 0.0,
                "verified": False,
                "meets_threshold": self.config.fallback_on_error,
                "threshold_used": min_threshold,
                "vouch_count": 0,
                "capabilities": [],
                "tier": None,
                "badges": [],
                "error": f"Connection error: {e}",
                "fallback_used": self.config.fallback_on_error
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Joy Trust API error: {e.response.status_code}")
            return {
                "agent_name": agent_name,
                "agent_id": None,
                "trust_score": 0.0,
                "verified": False,
                "meets_threshold": self.config.fallback_on_error,
                "threshold_used": min_threshold,
                "vouch_count": 0,
                "capabilities": [],
                "tier": None,
                "badges": [],
                "error": f"API error ({e.response.status_code}): {e.response.text}",
                "fallback_used": self.config.fallback_on_error
            }
        except Exception as e:
            logger.error(f"Joy Trust unexpected error: {e}")
            return {
                "agent_name": agent_name,
                "agent_id": None,
                "trust_score": 0.0,
                "verified": False,
                "meets_threshold": self.config.fallback_on_error,
                "threshold_used": min_threshold,
                "vouch_count": 0,
                "capabilities": [],
                "tier": None,
                "badges": [],
                "error": f"Unexpected error: {e}",
                "fallback_used": self.config.fallback_on_error
            }
    
    def verify_handoff_safety(self, agent_name: str, min_score: Optional[float] = None) -> Dict[str, Any]:
        """Verify if it's safe to hand off to the specified agent.
        
        Args:
            agent_name: Target agent for handoff
            min_score: Minimum acceptable trust score
            
        Returns:
            Dictionary with safety verification and recommendation
        """
        trust_result = self.check_trust(agent_name, min_score)
        
        safety_result = {
            **trust_result,
            "handoff_safe": trust_result.get("meets_threshold", False),
            "recommendation": self._get_handoff_recommendation(trust_result),
            "verification_time": time.time()
        }
        
        return safety_result
    
    def _get_handoff_recommendation(self, trust_result: Dict[str, Any]) -> str:
        """Generate handoff recommendation based on trust score."""
        score = trust_result.get("trust_score", 0.0)
        verified = trust_result.get("verified", False)
        error = trust_result.get("error")
        
        if error and not trust_result.get("fallback_used", False):
            return f"⚠️ Trust verification failed: {error}. Handoff not recommended."
        
        if error and trust_result.get("fallback_used", False):
            return "⚠️ Trust verification failed but fallback enabled. Proceed with caution."
        
        if score >= 4.5 and verified:
            return "✅ Excellent trust score. Handoff highly recommended."
        elif score >= 3.5 and verified:
            return "✅ Good trust score. Handoff recommended."
        elif score >= 2.5:
            return "⚠️ Moderate trust score. Handoff acceptable with caution."
        elif score >= 1.0:
            return "❌ Low trust score. Handoff not recommended."
        else:
            return "❌ Very low or no trust score. Handoff strongly discouraged."
    
    def configure(self, **kwargs) -> Dict[str, Any]:
        """Update configuration settings."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        return {
            "status": "configured",
            "config": {
                "enabled": self.config.enabled,
                "min_score": self.config.min_score,
                "auto_verify_handoffs": self.config.auto_verify_handoffs,
                "timeout_seconds": self.config.timeout_seconds
            }
        }


def trust_verified_handoff(min_score: float = 3.0, trust_tool: Optional[JoyTrustTool] = None):
    """Decorator for trust-verified agent handoffs.
    
    This decorator automatically verifies agent trust before delegation.
    
    Args:
        min_score: Minimum trust score required
        trust_tool: Custom JoyTrustTool instance (creates one if None)
    
    Usage:
        @trust_verified_handoff(min_score=4.0)
        def delegate_task(agent_name, task):
            # Your delegation logic here
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get agent name from args/kwargs
            agent_name = None
            if args and hasattr(args[0], 'name'):
                agent_name = args[0].name
            elif 'agent_name' in kwargs:
                agent_name = kwargs['agent_name']
            elif 'agent' in kwargs and hasattr(kwargs['agent'], 'name'):
                agent_name = kwargs['agent'].name
            
            if not agent_name:
                logger.warning("Could not determine agent name for trust verification")
                return func(*args, **kwargs)
            
            # Verify trust if enabled
            config = TrustConfig.from_env()
            if config.enabled and config.auto_verify_handoffs:
                tool = trust_tool or JoyTrustTool(config=config)
                verification = tool.verify_handoff_safety(agent_name, min_score)
                
                if not verification.get("handoff_safe", False):
                    error_msg = f"Handoff blocked: {verification.get('recommendation', 'Trust verification failed')}"
                    logger.warning(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "trust_verification": verification
                    }
                
                logger.info(f"Trust verification passed for {agent_name}: {verification.get('recommendation')}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def check_trust_score(agent_name: str, min_score: float = 3.0) -> Dict[str, Any]:
    """Check an agent's trust score on Joy Trust Network before delegation.
    
    Args:
        agent_name: Name/identifier of the agent to check
        min_score: Minimum acceptable trust score
    
    Returns:
        Dictionary containing trust information and safety recommendation
    """
    tool = JoyTrustTool()
    return tool.check_trust(agent_name=agent_name, min_score=min_score)


def verify_handoff_safety(agent_name: str, min_score: float = 3.0) -> Dict[str, Any]:
    """Verify if it's safe to hand off to the specified agent.
    
    Args:
        agent_name: Target agent for handoff
        min_score: Minimum acceptable trust score
        
    Returns:
        Dictionary with safety verification and recommendation
    """
    tool = JoyTrustTool()
    return tool.verify_handoff_safety(agent_name=agent_name, min_score=min_score)


def is_trust_verification_enabled() -> bool:
    """Check if trust verification is enabled via environment variables."""
    config = TrustConfig.from_env()
    return config.enabled


def get_trust_config() -> TrustConfig:
    """Get current trust configuration from environment variables."""
    return TrustConfig.from_env()