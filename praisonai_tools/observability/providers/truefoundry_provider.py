"""
TrueFoundry Provider

Integration with TrueFoundry for LLM observability.
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


class TrueFoundryProvider(BaseObservabilityProvider):
    """TrueFoundry observability provider."""
    
    name = "truefoundry"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize TrueFoundry provider."""
        super().__init__(config)
    
    def is_available(self) -> bool:
        """Check if truefoundry SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("truefoundry") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize TrueFoundry."""
        api_key = kwargs.get("api_key") or os.getenv("TRUEFOUNDRY_API_KEY")
        if not api_key:
            return False
        self._initialized = True
        return True
    
    def shutdown(self) -> None:
        """Shutdown TrueFoundry provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check TrueFoundry connection."""
        if not self._initialized:
            return False, "TrueFoundry not initialized"
        return True, "TrueFoundry configured"
    
    def export_span(self, span: Span) -> bool:
        """Export span to TrueFoundry."""
        return self._initialized
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to TrueFoundry."""
        return self._initialized


ObservabilityManager.register_provider("truefoundry", TrueFoundryProvider)
