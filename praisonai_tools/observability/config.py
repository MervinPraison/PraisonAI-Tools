"""
Observability Configuration

Unified configuration for all observability providers.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ObservabilityConfig:
    """Configuration for observability providers."""
    
    # Provider selection
    provider: Optional[str] = None  # Auto-detect if None
    
    # Common settings
    project_name: Optional[str] = None
    session_id: Optional[str] = None
    run_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Tracing settings
    enabled: bool = True
    trace_llm_calls: bool = True
    trace_tool_calls: bool = True
    trace_agent_steps: bool = True
    
    # Multi-agent settings
    propagate_context: bool = True
    parent_trace_id: Optional[str] = None
    
    # Performance settings
    batch_size: int = 100
    flush_interval: float = 5.0
    async_export: bool = True
    
    # Redaction settings
    redact_inputs: bool = False
    redact_outputs: bool = False
    redaction_patterns: List[str] = field(default_factory=list)
    
    # Provider-specific settings
    extra: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_env(cls) -> "ObservabilityConfig":
        """Create config from environment variables."""
        return cls(
            provider=os.getenv("PRAISONAI_OBS_PROVIDER"),
            project_name=os.getenv("PRAISONAI_OBS_PROJECT"),
            session_id=os.getenv("PRAISONAI_OBS_SESSION_ID"),
            run_id=os.getenv("PRAISONAI_OBS_RUN_ID"),
            user_id=os.getenv("PRAISONAI_OBS_USER_ID"),
            enabled=os.getenv("PRAISONAI_OBS_ENABLED", "true").lower() == "true",
            trace_llm_calls=os.getenv("PRAISONAI_OBS_TRACE_LLM", "true").lower() == "true",
            trace_tool_calls=os.getenv("PRAISONAI_OBS_TRACE_TOOLS", "true").lower() == "true",
            trace_agent_steps=os.getenv("PRAISONAI_OBS_TRACE_AGENTS", "true").lower() == "true",
            propagate_context=os.getenv("PRAISONAI_OBS_PROPAGATE", "true").lower() == "true",
            batch_size=int(os.getenv("PRAISONAI_OBS_BATCH_SIZE", "100")),
            flush_interval=float(os.getenv("PRAISONAI_OBS_FLUSH_INTERVAL", "5.0")),
            async_export=os.getenv("PRAISONAI_OBS_ASYNC", "true").lower() == "true",
            redact_inputs=os.getenv("PRAISONAI_OBS_REDACT_INPUTS", "false").lower() == "true",
            redact_outputs=os.getenv("PRAISONAI_OBS_REDACT_OUTPUTS", "false").lower() == "true",
        )
    
    def merge(self, **kwargs) -> "ObservabilityConfig":
        """Create a new config with merged values."""
        current = {
            "provider": self.provider,
            "project_name": self.project_name,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "user_id": self.user_id,
            "enabled": self.enabled,
            "trace_llm_calls": self.trace_llm_calls,
            "trace_tool_calls": self.trace_tool_calls,
            "trace_agent_steps": self.trace_agent_steps,
            "propagate_context": self.propagate_context,
            "parent_trace_id": self.parent_trace_id,
            "batch_size": self.batch_size,
            "flush_interval": self.flush_interval,
            "async_export": self.async_export,
            "redact_inputs": self.redact_inputs,
            "redact_outputs": self.redact_outputs,
            "redaction_patterns": self.redaction_patterns.copy(),
            "extra": self.extra.copy(),
        }
        current.update({k: v for k, v in kwargs.items() if v is not None})
        return ObservabilityConfig(**current)


# Provider environment variable mappings
PROVIDER_ENV_KEYS = {
    "agentops": ["AGENTOPS_API_KEY"],
    "langfuse": ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"],
    "langsmith": ["LANGSMITH_API_KEY"],
    "traceloop": ["TRACELOOP_API_KEY"],
    "arize_phoenix": ["PHOENIX_API_KEY"],
    "openlit": ["OPENLIT_API_KEY"],
    "langtrace": ["LANGTRACE_API_KEY"],
    "langwatch": ["LANGWATCH_API_KEY"],
    "datadog": ["DD_API_KEY"],
    "mlflow": ["MLFLOW_TRACKING_URI"],
    "opik": ["OPIK_API_KEY", "COMET_API_KEY"],
    "portkey": ["PORTKEY_API_KEY"],
    "braintrust": ["BRAINTRUST_API_KEY"],
    "maxim": ["MAXIM_API_KEY"],
    "weave": ["WANDB_API_KEY"],
    "neatlogs": ["NEATLOGS_API_KEY"],
    "langdb": ["LANGDB_API_KEY"],
    "atla": ["ATLA_API_KEY"],
    "patronus": ["PATRONUS_API_KEY"],
    "truefoundry": ["TRUEFOUNDRY_API_KEY"],
}


def detect_provider() -> Optional[str]:
    """Auto-detect available provider from environment variables."""
    for provider, keys in PROVIDER_ENV_KEYS.items():
        if all(os.getenv(key) for key in keys):
            return provider
    return None
