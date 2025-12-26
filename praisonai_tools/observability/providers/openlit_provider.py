"""
OpenLIT Provider

Integration with OpenLIT for universal LLM observability.
https://github.com/openlit/openlit
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


class OpenLITProvider(BaseObservabilityProvider):
    """OpenLIT observability provider - universal OTel bridge."""
    
    name = "openlit"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize OpenLIT provider."""
        super().__init__(config)
        self._openlit = None
    
    def is_available(self) -> bool:
        """Check if openlit SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("openlit") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize OpenLIT."""
        if not self.is_available():
            return False
        
        try:
            import openlit
            
            otlp_endpoint = kwargs.get("otlp_endpoint") or os.getenv(
                "OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318"
            )
            disable_batch = kwargs.get("disable_batch", False)
            disable_metrics = kwargs.get("disable_metrics", False)
            
            # Initialize OpenLIT
            openlit.init(
                otlp_endpoint=otlp_endpoint,
                disable_batch=disable_batch,
                disable_metrics=disable_metrics,
            )
            
            self._openlit = openlit
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"OpenLIT init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown OpenLIT provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check OpenLIT connection."""
        if not self._initialized:
            return False, "OpenLIT not initialized"
        
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if endpoint:
            return True, f"OpenLIT configured with endpoint: {endpoint}"
        return True, "OpenLIT initialized with default endpoint"
    
    def export_span(self, span: Span) -> bool:
        """Export span via OpenLIT."""
        if not self._initialized:
            return False
        # OpenLIT auto-instruments
        return True
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace via OpenLIT."""
        if not self._initialized:
            return False
        return True


# Auto-register provider
ObservabilityManager.register_provider("openlit", OpenLITProvider)
