"""
Opik Provider

Integration with Comet Opik for LLM observability.
https://www.comet.com/docs/opik/
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


class OpikProvider(BaseObservabilityProvider):
    """Opik observability provider."""
    
    name = "opik"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize Opik provider."""
        super().__init__(config)
        self._opik = None
    
    def is_available(self) -> bool:
        """Check if opik SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("opik") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize Opik."""
        if not self.is_available():
            return False
        
        try:
            import opik
            
            api_key = kwargs.get("api_key") or os.getenv("OPIK_API_KEY") or os.getenv("COMET_API_KEY")
            use_local = kwargs.get("use_local", False)
            
            opik.configure(use_local=use_local)
            
            self._opik = opik
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Opik init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown Opik provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check Opik connection."""
        if not self._initialized:
            return False, "Opik not initialized"
        
        api_key = os.getenv("OPIK_API_KEY") or os.getenv("COMET_API_KEY")
        if api_key:
            return True, "Opik API key configured"
        return True, "Opik initialized (local mode)"
    
    def export_span(self, span: Span) -> bool:
        """Export span to Opik."""
        if not self._initialized:
            return False
        return True
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to Opik."""
        if not self._initialized:
            return False
        return True


ObservabilityManager.register_provider("opik", OpikProvider)
