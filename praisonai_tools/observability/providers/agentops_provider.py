"""
AgentOps Provider

Integration with AgentOps for agent observability.
https://agentops.ai/
"""

import os
from typing import Any, Dict, Optional

from praisonai_tools.observability.base import (
    BaseObservabilityProvider,
    Span,
    SpanStatus,
    Trace,
)
from praisonai_tools.observability.config import ObservabilityConfig
from praisonai_tools.observability.manager import ObservabilityManager


class AgentOpsProvider(BaseObservabilityProvider):
    """AgentOps observability provider."""
    
    name = "agentops"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize AgentOps provider."""
        super().__init__(config)
        self._client = None
        self._session = None
    
    def is_available(self) -> bool:
        """Check if agentops SDK is available."""
        try:
            import agentops
            return True
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize AgentOps."""
        if not self.is_available():
            return False
        
        try:
            import agentops
            
            api_key = kwargs.get("api_key") or os.getenv("AGENTOPS_API_KEY")
            
            if not api_key:
                return False
            
            # Initialize AgentOps
            agentops.init(
                api_key=api_key,
                default_tags=kwargs.get("tags", []),
                auto_start_session=kwargs.get("auto_start_session", True),
            )
            
            self._client = agentops
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"AgentOps init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown AgentOps."""
        if self._client and self._session:
            try:
                self._client.end_session()
            except Exception:
                pass
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check AgentOps connection."""
        if not self._initialized:
            return False, "AgentOps not initialized"
        
        try:
            # AgentOps doesn't have a direct ping method
            # Check if we have a valid API key
            api_key = os.getenv("AGENTOPS_API_KEY")
            if api_key:
                return True, "AgentOps API key configured"
            return False, "AGENTOPS_API_KEY not set"
        except Exception as e:
            return False, str(e)
    
    def export_span(self, span: Span) -> bool:
        """Export span to AgentOps."""
        if not self._initialized or not self._client:
            return False
        
        try:
            # AgentOps auto-instruments, but we can record events
            if span.error_message:
                self._client.record(
                    self._client.ErrorEvent(
                        error_type=span.error_type or "Error",
                        details=span.error_message,
                    )
                )
            return True
        except Exception:
            return False
    
    def export_trace(self, trace: Trace) -> bool:
        """Export trace to AgentOps."""
        if not self._initialized:
            return False
        
        # AgentOps handles traces automatically via sessions
        return True


# Auto-register provider
ObservabilityManager.register_provider("agentops", AgentOpsProvider)
