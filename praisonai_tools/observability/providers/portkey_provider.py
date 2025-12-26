"""
Portkey Provider

Integration with Portkey for LLM gateway and observability.
https://portkey.ai/
"""

import os
from typing import Optional

from praisonai_tools.observability.base import (
    BaseObservabilityProvider,
    Span,
    Trace,
)
from praisonai_tools.observability.config import ObservabilityConfig
from praisonai_tools.observability.manager import ObservabilityManager


class PortkeyProvider(BaseObservabilityProvider):
    """Portkey observability provider."""
    
    name = "portkey"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize Portkey provider."""
        super().__init__(config)
        self._portkey = None
        self._gateway_url = None
    
    def is_available(self) -> bool:
        """Check if portkey SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("portkey_ai") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize Portkey."""
        if not self.is_available():
            return False
        
        try:
            from portkey_ai import PORTKEY_GATEWAY_URL
            
            api_key = kwargs.get("api_key") or os.getenv("PORTKEY_API_KEY")
            
            if not api_key:
                return False
            
            self._gateway_url = PORTKEY_GATEWAY_URL
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Portkey init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown Portkey provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check Portkey connection."""
        if not self._initialized:
            return False, "Portkey not initialized"
        
        api_key = os.getenv("PORTKEY_API_KEY")
        if api_key:
            return True, "Portkey API key configured"
        return False, "PORTKEY_API_KEY not set"
    
    def get_headers(self, virtual_key: str = None, trace_id: str = None):
        """Get Portkey headers for LLM requests."""
        if not self.is_available():
            return {}
        
        try:
            from portkey_ai import createHeaders
            
            api_key = os.getenv("PORTKEY_API_KEY")
            return createHeaders(
                api_key=api_key,
                virtual_key=virtual_key,
                trace_id=trace_id,
            )
        except Exception:
            return {}
    
    def export_span(self, span: Span) -> bool:
        """Export span to Portkey."""
        if not self._initialized:
            return False
        return True
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to Portkey."""
        if not self._initialized:
            return False
        return True


ObservabilityManager.register_provider("portkey", PortkeyProvider)
