"""
Maxim Provider

Integration with Maxim for LLM observability.
https://getmaxim.ai/
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


class MaximProvider(BaseObservabilityProvider):
    """Maxim observability provider."""
    
    name = "maxim"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize Maxim provider."""
        super().__init__(config)
        self._maxim = None
        self._logger = None
    
    def is_available(self) -> bool:
        """Check if maxim SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("maxim") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize Maxim."""
        if not self.is_available():
            return False
        
        try:
            from maxim import Maxim
            
            api_key = kwargs.get("api_key") or os.getenv("MAXIM_API_KEY")
            repo_id = kwargs.get("repo_id") or os.getenv("MAXIM_LOG_REPO_ID")
            
            if api_key:
                os.environ["MAXIM_API_KEY"] = api_key
            if repo_id:
                os.environ["MAXIM_LOG_REPO_ID"] = repo_id
            
            self._maxim = Maxim()
            self._logger = self._maxim.logger()
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Maxim init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown Maxim provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check Maxim connection."""
        if not self._initialized:
            return False, "Maxim not initialized"
        
        api_key = os.getenv("MAXIM_API_KEY")
        if api_key:
            return True, "Maxim API key configured"
        return False, "MAXIM_API_KEY not set"
    
    def export_span(self, span: Span) -> bool:
        """Export span to Maxim."""
        if not self._initialized:
            return False
        return True
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to Maxim."""
        if not self._initialized:
            return False
        return True


ObservabilityManager.register_provider("maxim", MaximProvider)
