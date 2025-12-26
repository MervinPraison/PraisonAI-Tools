"""
Arize Phoenix Provider

Integration with Arize Phoenix for LLM observability.
https://phoenix.arize.com/
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


class ArizePhoenixProvider(BaseObservabilityProvider):
    """Arize Phoenix observability provider."""
    
    name = "arize_phoenix"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize Arize Phoenix provider."""
        super().__init__(config)
        self._tracer_provider = None
    
    def is_available(self) -> bool:
        """Check if phoenix SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("phoenix.otel") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize Arize Phoenix."""
        if not self.is_available():
            return False
        
        try:
            from phoenix.otel import register
            
            api_key = kwargs.get("api_key") or os.getenv("PHOENIX_API_KEY")
            endpoint = kwargs.get("endpoint") or os.getenv(
                "PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com/"
            )
            project_name = kwargs.get("project_name") or self.config.project_name or "default"
            
            # Set environment variables
            if api_key:
                os.environ["PHOENIX_API_KEY"] = api_key
            os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = endpoint
            
            # Register Phoenix tracer
            self._tracer_provider = register(
                project_name=project_name,
                auto_instrument=kwargs.get("auto_instrument", True),
            )
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Arize Phoenix init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown Arize Phoenix provider."""
        if self._tracer_provider:
            try:
                self._tracer_provider.shutdown()
            except Exception:
                pass
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check Arize Phoenix connection."""
        if not self._initialized:
            return False, "Arize Phoenix not initialized"
        
        api_key = os.getenv("PHOENIX_API_KEY")
        if api_key:
            return True, "Phoenix API key configured"
        return False, "PHOENIX_API_KEY not set"
    
    def export_span(self, span: Span) -> bool:
        """Export span to Arize Phoenix."""
        if not self._initialized:
            return False
        # Phoenix auto-instruments via OpenInference
        return True
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to Arize Phoenix."""
        if not self._initialized:
            return False
        return True


# Auto-register provider
ObservabilityManager.register_provider("arize_phoenix", ArizePhoenixProvider)
