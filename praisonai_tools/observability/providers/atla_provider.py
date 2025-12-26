"""
Atla Provider

Integration with Atla for LLM observability.
https://app.atla-ai.com/
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


class AtlaProvider(BaseObservabilityProvider):
    """Atla observability provider."""
    
    name = "atla"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize Atla provider."""
        super().__init__(config)
        self._atla = None
    
    def is_available(self) -> bool:
        """Check if atla SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("atla_insights") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize Atla."""
        if not self.is_available():
            return False
        
        try:
            from atla_insights import configure
            
            api_key = kwargs.get("api_key") or os.getenv("ATLA_API_KEY")
            
            if not api_key:
                return False
            
            configure(token=api_key)
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Atla init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown Atla provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check Atla connection."""
        if not self._initialized:
            return False, "Atla not initialized"
        
        api_key = os.getenv("ATLA_API_KEY")
        if api_key:
            return True, "Atla API key configured"
        return False, "ATLA_API_KEY not set"
    
    def instrument(self, provider: str = "openai"):
        """Get Atla instrumentation context manager."""
        if not self.is_available():
            from contextlib import nullcontext
            return nullcontext()
        
        try:
            from atla_insights import instrument_agno
            return instrument_agno(provider)
        except ImportError:
            from contextlib import nullcontext
            return nullcontext()
    
    def export_span(self, span: Span) -> bool:
        """Export span to Atla."""
        return self._initialized
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to Atla."""
        return self._initialized


ObservabilityManager.register_provider("atla", AtlaProvider)
