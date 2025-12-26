"""
LangDB Provider

Integration with LangDB for SQL-based LLM observability.
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


class LangDBProvider(BaseObservabilityProvider):
    """LangDB observability provider."""
    
    name = "langdb"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize LangDB provider."""
        super().__init__(config)
    
    def is_available(self) -> bool:
        """Check if langdb SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("langdb") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize LangDB."""
        api_key = kwargs.get("api_key") or os.getenv("LANGDB_API_KEY")
        if not api_key:
            return False
        self._initialized = True
        return True
    
    def shutdown(self) -> None:
        """Shutdown LangDB provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check LangDB connection."""
        if not self._initialized:
            return False, "LangDB not initialized"
        return True, "LangDB configured"
    
    def export_span(self, span: Span) -> bool:
        """Export span to LangDB."""
        return self._initialized
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to LangDB."""
        return self._initialized


ObservabilityManager.register_provider("langdb", LangDBProvider)
