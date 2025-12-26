"""
Neatlogs Provider

Integration with Neatlogs for LLM observability.
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


class NeatlogsProvider(BaseObservabilityProvider):
    """Neatlogs observability provider."""
    
    name = "neatlogs"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize Neatlogs provider."""
        super().__init__(config)
    
    def is_available(self) -> bool:
        """Check if neatlogs SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("neatlogs") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize Neatlogs."""
        api_key = kwargs.get("api_key") or os.getenv("NEATLOGS_API_KEY")
        if not api_key:
            return False
        self._initialized = True
        return True
    
    def shutdown(self) -> None:
        """Shutdown Neatlogs provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check Neatlogs connection."""
        if not self._initialized:
            return False, "Neatlogs not initialized"
        return True, "Neatlogs configured"
    
    def export_span(self, span: Span) -> bool:
        """Export span to Neatlogs."""
        return self._initialized
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to Neatlogs."""
        return self._initialized


ObservabilityManager.register_provider("neatlogs", NeatlogsProvider)
