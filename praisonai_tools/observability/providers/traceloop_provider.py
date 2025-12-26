"""
Traceloop Provider

Integration with Traceloop for LLM observability.
https://traceloop.com/
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


class TraceloopProvider(BaseObservabilityProvider):
    """Traceloop observability provider."""
    
    name = "traceloop"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize Traceloop provider."""
        super().__init__(config)
        self._sdk = None
    
    def is_available(self) -> bool:
        """Check if traceloop SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("traceloop.sdk") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize Traceloop."""
        if not self.is_available():
            return False
        
        try:
            from traceloop.sdk import Traceloop
            
            api_key = kwargs.get("api_key") or os.getenv("TRACELOOP_API_KEY")
            app_name = kwargs.get("app_name") or self.config.project_name or "praisonai"
            
            # Initialize Traceloop
            Traceloop.init(
                app_name=app_name,
                api_key=api_key,
                disable_batch=kwargs.get("disable_batch", False),
            )
            
            self._sdk = Traceloop
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Traceloop init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown Traceloop provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check Traceloop connection."""
        if not self._initialized:
            return False, "Traceloop not initialized"
        
        api_key = os.getenv("TRACELOOP_API_KEY")
        if api_key:
            return True, "Traceloop API key configured"
        return False, "TRACELOOP_API_KEY not set"
    
    def export_span(self, span: Span) -> bool:
        """Export span to Traceloop."""
        if not self._initialized:
            return False
        # Traceloop auto-instruments via OpenTelemetry
        return True
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to Traceloop."""
        if not self._initialized:
            return False
        return True
    
    def workflow(self, name: str):
        """Decorator for workflow tracing."""
        if not self._initialized:
            def noop(func):
                return func
            return noop
        
        try:
            from traceloop.sdk.decorators import workflow
            return workflow(name=name)
        except ImportError:
            def noop(func):
                return func
            return noop


# Auto-register provider
ObservabilityManager.register_provider("traceloop", TraceloopProvider)
