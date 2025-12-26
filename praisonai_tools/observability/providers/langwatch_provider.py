"""
LangWatch Provider

Integration with LangWatch for LLM observability.
https://langwatch.ai/
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


class LangWatchProvider(BaseObservabilityProvider):
    """LangWatch observability provider."""
    
    name = "langwatch"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize LangWatch provider."""
        super().__init__(config)
        self._langwatch = None
    
    def is_available(self) -> bool:
        """Check if langwatch SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("langwatch") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize LangWatch."""
        if not self.is_available():
            return False
        
        try:
            import langwatch
            
            api_key = kwargs.get("api_key") or os.getenv("LANGWATCH_API_KEY")
            
            if api_key:
                os.environ["LANGWATCH_API_KEY"] = api_key
            
            instrumentors = kwargs.get("instrumentors", [])
            langwatch.setup(instrumentors=instrumentors)
            
            self._langwatch = langwatch
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"LangWatch init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown LangWatch provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check LangWatch connection."""
        if not self._initialized:
            return False, "LangWatch not initialized"
        
        api_key = os.getenv("LANGWATCH_API_KEY")
        if api_key:
            return True, "LangWatch API key configured"
        return False, "LANGWATCH_API_KEY not set"
    
    def export_span(self, span: Span) -> bool:
        """Export span to LangWatch."""
        if not self._initialized:
            return False
        return True
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to LangWatch."""
        if not self._initialized:
            return False
        return True


# Auto-register provider
ObservabilityManager.register_provider("langwatch", LangWatchProvider)
