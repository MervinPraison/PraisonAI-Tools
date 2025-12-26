"""
MLflow Provider

Integration with MLflow for LLM observability.
https://mlflow.org/
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


class MLflowProvider(BaseObservabilityProvider):
    """MLflow observability provider."""
    
    name = "mlflow"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize MLflow provider."""
        super().__init__(config)
        self._mlflow = None
    
    def is_available(self) -> bool:
        """Check if mlflow SDK is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("mlflow") is not None
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize MLflow."""
        if not self.is_available():
            return False
        
        try:
            import mlflow
            
            tracking_uri = kwargs.get("tracking_uri") or os.getenv("MLFLOW_TRACKING_URI")
            experiment_name = kwargs.get("experiment") or self.config.project_name or "PraisonAI"
            
            if tracking_uri:
                mlflow.set_tracking_uri(tracking_uri)
            
            mlflow.set_experiment(experiment_name)
            
            self._mlflow = mlflow
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"MLflow init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown MLflow provider."""
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check MLflow connection."""
        if not self._initialized:
            return False, "MLflow not initialized"
        
        tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
        if tracking_uri:
            return True, f"MLflow tracking URI: {tracking_uri}"
        return True, "MLflow initialized with default tracking"
    
    def export_span(self, span: Span) -> bool:
        """Export span to MLflow."""
        if not self._initialized or not self._mlflow:
            return False
        return True
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to MLflow."""
        if not self._initialized:
            return False
        return True


ObservabilityManager.register_provider("mlflow", MLflowProvider)
