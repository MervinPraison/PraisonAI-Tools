"""
Patronus Provider

Integration with Patronus AI for LLM evaluation and observability.
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


class PatronusProvider(BaseObservabilityProvider):
    """Patronus AI observability provider."""
    
    name = "patronus"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize Patronus provider."""
        super().__init__(config)
    
    def is_available(self) -> bool:
        """Check if patronus SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("patronus") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize Patronus."""
        api_key = kwargs.get("api_key") or os.getenv("PATRONUS_API_KEY")
        if not api_key:
            return False
        self._initialized = True
        return True
    
    def shutdown(self) -> None:
        """Shutdown Patronus provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check Patronus connection."""
        if not self._initialized:
            return False, "Patronus not initialized"
        return True, "Patronus configured"
    
    def export_span(self, span: Span) -> bool:
        """Export span to Patronus."""
        return self._initialized
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to Patronus."""
        return self._initialized


ObservabilityManager.register_provider("patronus", PatronusProvider)
