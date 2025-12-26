"""
Observability Manager

Central manager for all observability providers.
"""

import os
from typing import Any, Dict, List, Optional, Type

from praisonai_tools.observability.base import (
    BaseObservabilityProvider,
    Span,
    SpanKind,
    SpanStatus,
    Trace,
)
from praisonai_tools.observability.config import (
    ObservabilityConfig,
    PROVIDER_ENV_KEYS,
    detect_provider,
)


class ObservabilityManager:
    """
    Central manager for observability providers.
    
    Usage:
        from praisonai_tools.observability import obs
        
        # Auto-detect provider from env vars
        obs.init()
        
        # Or specify provider
        obs.init(provider="langfuse")
        
        # Use context managers
        with obs.trace("my-workflow"):
            with obs.span("step-1", kind=SpanKind.AGENT):
                # do work
                pass
    """
    
    _instance: Optional["ObservabilityManager"] = None
    _providers: Dict[str, Type[BaseObservabilityProvider]] = {}
    
    def __new__(cls) -> "ObservabilityManager":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the manager."""
        if self._initialized:
            return
        
        self.config: Optional[ObservabilityConfig] = None
        self._provider: Optional[BaseObservabilityProvider] = None
        self._initialized = True
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseObservabilityProvider]) -> None:
        """Register a provider class."""
        cls._providers[name] = provider_class
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """List all registered providers."""
        return list(cls._providers.keys())
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get providers that have required env vars set."""
        available = []
        for name in cls._providers:
            if name in PROVIDER_ENV_KEYS:
                keys = PROVIDER_ENV_KEYS[name]
                if all(os.getenv(key) for key in keys):
                    available.append(name)
        return available
    
    def init(
        self,
        provider: Optional[str] = None,
        project_name: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Initialize observability with a provider.
        
        Args:
            provider: Provider name (auto-detect if None)
            project_name: Project/app name for traces
            session_id: Session identifier
            **kwargs: Additional provider-specific config
            
        Returns:
            True if initialization successful
        """
        # Build config
        self.config = ObservabilityConfig.from_env().merge(
            provider=provider,
            project_name=project_name,
            session_id=session_id,
            extra=kwargs,
        )
        
        # Auto-detect provider if not specified
        provider_name = self.config.provider or detect_provider()
        
        if not provider_name:
            # No provider configured - silent no-op mode
            return False
        
        # Get provider class
        if provider_name not in self._providers:
            # Try to load provider dynamically
            self._load_provider(provider_name)
        
        if provider_name not in self._providers:
            return False
        
        # Instantiate and initialize provider
        provider_class = self._providers[provider_name]
        self._provider = provider_class(self.config)
        
        return self._provider.init(**kwargs)
    
    def _load_provider(self, name: str) -> None:
        """Dynamically load a provider module."""
        provider_modules = {
            "agentops": "agentops_provider",
            "langfuse": "langfuse_provider",
            "langsmith": "langsmith_provider",
            "traceloop": "traceloop_provider",
            "arize_phoenix": "arize_phoenix_provider",
            "openlit": "openlit_provider",
            "langtrace": "langtrace_provider",
            "langwatch": "langwatch_provider",
            "datadog": "datadog_provider",
            "mlflow": "mlflow_provider",
            "opik": "opik_provider",
            "portkey": "portkey_provider",
            "braintrust": "braintrust_provider",
            "maxim": "maxim_provider",
            "weave": "weave_provider",
            "neatlogs": "neatlogs_provider",
            "langdb": "langdb_provider",
            "atla": "atla_provider",
            "patronus": "patronus_provider",
            "truefoundry": "truefoundry_provider",
        }
        
        if name in provider_modules:
            try:
                import importlib
                module = importlib.import_module(
                    f"praisonai_tools.observability.providers.{provider_modules[name]}"
                )
                # Provider should auto-register on import
            except ImportError:
                pass
    
    def shutdown(self) -> None:
        """Shutdown the current provider."""
        if self._provider:
            self._provider.shutdown()
            self._provider = None
    
    @property
    def provider(self) -> Optional[BaseObservabilityProvider]:
        """Get the current provider."""
        return self._provider
    
    @property
    def enabled(self) -> bool:
        """Check if observability is enabled."""
        return self._provider is not None and self._provider._initialized
    
    def doctor(self) -> Dict[str, Any]:
        """
        Run diagnostics on observability setup.
        
        Returns:
            Dict with diagnostic results
        """
        results = {
            "enabled": self.enabled,
            "provider": self._provider.name if self._provider else None,
            "available_providers": self.get_available_providers(),
            "registered_providers": self.list_providers(),
            "connection_status": None,
            "connection_message": None,
        }
        
        if self._provider:
            success, message = self._provider.check_connection()
            results["connection_status"] = success
            results["connection_message"] = message
        
        return results
    
    # Delegate methods to provider
    
    def trace(self, name: str, **kwargs):
        """Start a trace context manager."""
        if self._provider:
            return self._provider.trace(name, **kwargs)
        return _NoOpContextManager()
    
    def span(self, name: str, kind: SpanKind = SpanKind.CUSTOM, **kwargs):
        """Start a span context manager."""
        if self._provider:
            return self._provider.span(name, kind, **kwargs)
        return _NoOpContextManager()
    
    def start_trace(self, name: str, **kwargs) -> Optional[Trace]:
        """Start a new trace."""
        if self._provider:
            return self._provider.start_trace(name, **kwargs)
        return None
    
    def end_trace(self, trace: Optional[Trace] = None) -> None:
        """End a trace."""
        if self._provider:
            self._provider.end_trace(trace)
    
    def start_span(self, name: str, kind: SpanKind = SpanKind.CUSTOM, **kwargs) -> Optional[Span]:
        """Start a new span."""
        if self._provider:
            return self._provider.start_span(name, kind, **kwargs)
        return None
    
    def end_span(self, span: Optional[Span] = None, status: SpanStatus = SpanStatus.OK) -> None:
        """End a span."""
        if self._provider:
            self._provider.end_span(span, status)
    
    def log_llm_call(self, model: str, input_messages: Any, output: Any, **kwargs) -> Optional[Span]:
        """Log an LLM call."""
        if self._provider:
            return self._provider.log_llm_call(model, input_messages, output, **kwargs)
        return None
    
    def log_tool_call(self, tool_name: str, tool_input: Any, tool_output: Any, **kwargs) -> Optional[Span]:
        """Log a tool call."""
        if self._provider:
            return self._provider.log_tool_call(tool_name, tool_input, tool_output, **kwargs)
        return None
    
    def log_agent_step(self, agent_name: str, step_name: str, input_data: Any, output_data: Any, **kwargs) -> Optional[Span]:
        """Log an agent step."""
        if self._provider:
            return self._provider.log_agent_step(agent_name, step_name, input_data, output_data, **kwargs)
        return None
    
    def decorator(self, name: Optional[str] = None, kind: SpanKind = SpanKind.CUSTOM):
        """Decorator to trace a function."""
        if self._provider:
            return self._provider.decorator(name, kind)
        
        # No-op decorator
        def noop(func):
            return func
        return noop


class _NoOpContextManager:
    """No-op context manager when observability is disabled."""
    
    def __enter__(self):
        return None
    
    def __exit__(self, *args):
        pass


# Auto-register built-in providers on first access
def _auto_register_providers():
    """Auto-register all built-in providers."""
    provider_classes = [
        ("agentops", "AgentOpsProvider", "agentops_provider"),
        ("langfuse", "LangfuseProvider", "langfuse_provider"),
        ("langsmith", "LangSmithProvider", "langsmith_provider"),
        ("traceloop", "TraceloopProvider", "traceloop_provider"),
        ("arize_phoenix", "ArizePhoenixProvider", "arize_phoenix_provider"),
        ("openlit", "OpenLITProvider", "openlit_provider"),
        ("langtrace", "LangtraceProvider", "langtrace_provider"),
        ("langwatch", "LangWatchProvider", "langwatch_provider"),
        ("datadog", "DatadogProvider", "datadog_provider"),
        ("mlflow", "MLflowProvider", "mlflow_provider"),
        ("opik", "OpikProvider", "opik_provider"),
        ("portkey", "PortkeyProvider", "portkey_provider"),
        ("braintrust", "BraintrustProvider", "braintrust_provider"),
        ("maxim", "MaximProvider", "maxim_provider"),
        ("weave", "WeaveProvider", "weave_provider"),
        ("neatlogs", "NeatlogsProvider", "neatlogs_provider"),
        ("langdb", "LangDBProvider", "langdb_provider"),
        ("atla", "AtlaProvider", "atla_provider"),
        ("patronus", "PatronusProvider", "patronus_provider"),
        ("truefoundry", "TrueFoundryProvider", "truefoundry_provider"),
    ]
    
    for name, class_name, module_name in provider_classes:
        try:
            import importlib
            module = importlib.import_module(
                f"praisonai_tools.observability.providers.{module_name}"
            )
            provider_class = getattr(module, class_name)
            ObservabilityManager.register_provider(name, provider_class)
        except (ImportError, AttributeError):
            pass  # Provider not available
