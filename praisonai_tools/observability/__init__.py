"""
PraisonAI Observability Suite

Unified observability integrations for PraisonAI agents.
All imports are lazy-loaded for zero performance impact when not in use.

Usage:
    from praisonai_tools.observability import obs
    
    # Auto-detect and configure
    obs.init()
    
    # Or use specific provider
    obs.init(provider="langfuse")
"""

__all__ = [
    # Core
    "obs",
    "ObservabilityManager",
    "ObservabilityConfig",
    # Providers
    "AgentOpsProvider",
    "LangfuseProvider",
    "LangSmithProvider",
    "TraceloopProvider",
    "ArizePhoenixProvider",
    "OpenLITProvider",
    "LangtraceProvider",
    "LangWatchProvider",
    "DatadogProvider",
    "MLflowProvider",
    "OpikProvider",
    "PortkeyProvider",
    "BraintrustProvider",
    "MaximProvider",
    "WeaveProvider",
    "NeatlogsProvider",
    "LangDBProvider",
    "AtlaProvider",
    "PatronusProvider",
    "TrueFoundryProvider",
]

# Lazy loading implementation
def __getattr__(name: str):
    """Lazy load observability components."""
    if name == "obs" or name == "ObservabilityManager":
        from praisonai_tools.observability.manager import ObservabilityManager
        if name == "obs":
            return ObservabilityManager()
        return ObservabilityManager
    
    if name == "ObservabilityConfig":
        from praisonai_tools.observability.config import ObservabilityConfig
        return ObservabilityConfig
    
    # Provider lazy loading
    provider_map = {
        "AgentOpsProvider": ("agentops_provider", "AgentOpsProvider"),
        "LangfuseProvider": ("langfuse_provider", "LangfuseProvider"),
        "LangSmithProvider": ("langsmith_provider", "LangSmithProvider"),
        "TraceloopProvider": ("traceloop_provider", "TraceloopProvider"),
        "ArizePhoenixProvider": ("arize_phoenix_provider", "ArizePhoenixProvider"),
        "OpenLITProvider": ("openlit_provider", "OpenLITProvider"),
        "LangtraceProvider": ("langtrace_provider", "LangtraceProvider"),
        "LangWatchProvider": ("langwatch_provider", "LangWatchProvider"),
        "DatadogProvider": ("datadog_provider", "DatadogProvider"),
        "MLflowProvider": ("mlflow_provider", "MLflowProvider"),
        "OpikProvider": ("opik_provider", "OpikProvider"),
        "PortkeyProvider": ("portkey_provider", "PortkeyProvider"),
        "BraintrustProvider": ("braintrust_provider", "BraintrustProvider"),
        "MaximProvider": ("maxim_provider", "MaximProvider"),
        "WeaveProvider": ("weave_provider", "WeaveProvider"),
        "NeatlogsProvider": ("neatlogs_provider", "NeatlogsProvider"),
        "LangDBProvider": ("langdb_provider", "LangDBProvider"),
        "AtlaProvider": ("atla_provider", "AtlaProvider"),
        "PatronusProvider": ("patronus_provider", "PatronusProvider"),
        "TrueFoundryProvider": ("truefoundry_provider", "TrueFoundryProvider"),
    }
    
    if name in provider_map:
        module_name, class_name = provider_map[name]
        import importlib
        module = importlib.import_module(f"praisonai_tools.observability.providers.{module_name}")
        return getattr(module, class_name)
    
    raise AttributeError(f"module 'praisonai_tools.observability' has no attribute '{name}'")
