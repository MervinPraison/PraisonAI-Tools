"""
Langtrace Provider

Integration with Langtrace for LLM observability.
https://langtrace.ai/
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


class LangtraceProvider(BaseObservabilityProvider):
    """Langtrace observability provider."""
    
    name = "langtrace"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize Langtrace provider."""
        super().__init__(config)
        self._langtrace = None
    
    def is_available(self) -> bool:
        """Check if langtrace SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("langtrace_python_sdk") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize Langtrace."""
        if not self.is_available():
            return False
        
        try:
            from langtrace_python_sdk import langtrace
            
            api_key = kwargs.get("api_key") or os.getenv("LANGTRACE_API_KEY")
            
            if api_key:
                os.environ["LANGTRACE_API_KEY"] = api_key
            
            langtrace.init()
            
            self._langtrace = langtrace
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Langtrace init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown Langtrace provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check Langtrace connection."""
        if not self._initialized:
            return False, "Langtrace not initialized"
        
        api_key = os.getenv("LANGTRACE_API_KEY")
        if api_key:
            return True, "Langtrace API key configured"
        return False, "LANGTRACE_API_KEY not set"
    
    def export_span(self, span: Span) -> bool:
        """Export span to Langtrace."""
        if not self._initialized:
            return False
        return True
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to Langtrace."""
        if not self._initialized:
            return False
        return True


# Auto-register provider
ObservabilityManager.register_provider("langtrace", LangtraceProvider)
