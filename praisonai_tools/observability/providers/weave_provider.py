"""
Weave Provider

Integration with Weights & Biases Weave for LLM observability.
https://weave-docs.wandb.ai/
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


class WeaveProvider(BaseObservabilityProvider):
    """Weave observability provider."""
    
    name = "weave"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize Weave provider."""
        super().__init__(config)
        self._weave = None
    
    def is_available(self) -> bool:
        """Check if weave SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("weave") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize Weave."""
        if not self.is_available():
            return False
        
        try:
            import weave
            
            project_name = kwargs.get("project_name") or self.config.project_name or "praisonai"
            
            weave.init(project_name=project_name)
            
            self._weave = weave
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Weave init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown Weave provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check Weave connection."""
        if not self._initialized:
            return False, "Weave not initialized"
        
        api_key = os.getenv("WANDB_API_KEY")
        if api_key:
            return True, "W&B API key configured"
        return True, "Weave initialized (may prompt for auth)"
    
    def op(self):
        """Get the weave.op decorator."""
        if not self._initialized or not self._weave:
            def noop(func):
                return func
            return noop
        return self._weave.op()
    
    def export_span(self, span: Span) -> bool:
        """Export span to Weave."""
        if not self._initialized:
            return False
        return True
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to Weave."""
        if not self._initialized:
            return False
        return True


ObservabilityManager.register_provider("weave", WeaveProvider)
