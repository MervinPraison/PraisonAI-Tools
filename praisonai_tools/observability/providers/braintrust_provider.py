"""
Braintrust Provider

Integration with Braintrust for LLM observability and evaluation.
https://www.braintrust.dev/
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


class BraintrustProvider(BaseObservabilityProvider):
    """Braintrust observability provider."""
    
    name = "braintrust"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize Braintrust provider."""
        super().__init__(config)
        self._tracer_provider = None
    
    def is_available(self) -> bool:
        """Check if braintrust SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("braintrust") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize Braintrust."""
        if not self.is_available():
            return False
        
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from braintrust.otel import BraintrustSpanProcessor
            
            api_key = kwargs.get("api_key") or os.getenv("BRAINTRUST_API_KEY")
            project = kwargs.get("project") or os.getenv("BRAINTRUST_PARENT", "praisonai")
            
            if not api_key:
                return False
            
            os.environ["BRAINTRUST_API_KEY"] = api_key
            os.environ["BRAINTRUST_PARENT"] = f"project_name:{project}"
            
            current_provider = trace.get_tracer_provider()
            if isinstance(current_provider, TracerProvider):
                provider = current_provider
            else:
                provider = TracerProvider()
                trace.set_tracer_provider(provider)
            
            provider.add_span_processor(BraintrustSpanProcessor())
            self._tracer_provider = provider
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Braintrust init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown Braintrust provider."""
        if self._tracer_provider:
            try:
                self._tracer_provider.shutdown()
            except Exception:
                pass
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check Braintrust connection."""
        if not self._initialized:
            return False, "Braintrust not initialized"
        
        api_key = os.getenv("BRAINTRUST_API_KEY")
        if api_key:
            return True, "Braintrust API key configured"
        return False, "BRAINTRUST_API_KEY not set"
    
    def export_span(self, span: Span) -> bool:
        """Export span to Braintrust."""
        if not self._initialized:
            return False
        return True
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to Braintrust."""
        if not self._initialized:
            return False
        return True


ObservabilityManager.register_provider("braintrust", BraintrustProvider)
