"""
Observability Providers

All provider implementations for the observability suite.
"""

__all__ = [
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


def __getattr__(name: str):
    """Lazy load provider classes."""
    provider_map = {
        "AgentOpsProvider": "agentops_provider",
        "LangfuseProvider": "langfuse_provider",
        "LangSmithProvider": "langsmith_provider",
        "TraceloopProvider": "traceloop_provider",
        "ArizePhoenixProvider": "arize_phoenix_provider",
        "OpenLITProvider": "openlit_provider",
        "LangtraceProvider": "langtrace_provider",
        "LangWatchProvider": "langwatch_provider",
        "DatadogProvider": "datadog_provider",
        "MLflowProvider": "mlflow_provider",
        "OpikProvider": "opik_provider",
        "PortkeyProvider": "portkey_provider",
        "BraintrustProvider": "braintrust_provider",
        "MaximProvider": "maxim_provider",
        "WeaveProvider": "weave_provider",
        "NeatlogsProvider": "neatlogs_provider",
        "LangDBProvider": "langdb_provider",
        "AtlaProvider": "atla_provider",
        "PatronusProvider": "patronus_provider",
        "TrueFoundryProvider": "truefoundry_provider",
    }
    
    if name in provider_map:
        import importlib
        module = importlib.import_module(
            f"praisonai_tools.observability.providers.{provider_map[name]}"
        )
        return getattr(module, name)
    
    raise AttributeError(f"module 'praisonai_tools.observability.providers' has no attribute '{name}'")
