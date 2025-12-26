"""
Datadog Provider

Integration with Datadog LLM Observability.
https://www.datadoghq.com/product/llm-observability/
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


class DatadogProvider(BaseObservabilityProvider):
    """Datadog LLM Observability provider."""
    
    name = "datadog"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize Datadog provider."""
        super().__init__(config)
        self._ddtrace = None
    
    def is_available(self) -> bool:
        """Check if ddtrace SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("ddtrace") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize Datadog."""
        if not self.is_available():
            return False
        
        try:
            api_key = kwargs.get("api_key") or os.getenv("DD_API_KEY")
            site = kwargs.get("site") or os.getenv("DD_SITE", "datadoghq.com")
            ml_app = kwargs.get("ml_app") or os.getenv("DD_LLMOBS_ML_APP", "praisonai")
            
            if not api_key:
                return False
            
            os.environ["DD_API_KEY"] = api_key
            os.environ["DD_SITE"] = site
            os.environ["DD_LLMOBS_ENABLED"] = "true"
            os.environ["DD_LLMOBS_ML_APP"] = ml_app
            os.environ["DD_LLMOBS_AGENTLESS_ENABLED"] = "true"
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Datadog init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown Datadog provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check Datadog connection."""
        if not self._initialized:
            return False, "Datadog not initialized"
        
        api_key = os.getenv("DD_API_KEY")
        if api_key:
            return True, "Datadog API key configured"
        return False, "DD_API_KEY not set"
    
    def export_span(self, span: Span) -> bool:
        """Export span to Datadog."""
        if not self._initialized:
            return False
        return True
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to Datadog."""
        if not self._initialized:
            return False
        return True


ObservabilityManager.register_provider("datadog", DatadogProvider)
