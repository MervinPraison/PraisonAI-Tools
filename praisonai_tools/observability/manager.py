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
        auto_instrument: bool = True,
        **kwargs
    ) -> bool:
        """
        Initialize observability with a provider.
        
        Args:
            provider: Provider name (auto-detect if None)
            project_name: Project/app name for traces
            session_id: Session identifier
            auto_instrument: If True (default), auto-instruments Agent/Agents/Workflow
                           classes so all operations are traced without explicit
                           obs.trace() wrappers
            **kwargs: Additional provider-specific config
            
        Returns:
            True if initialization successful
            
        Example:
            # Simplest usage - auto-detect provider and auto-instrument
            obs.init()
            
            # Explicit provider
            obs.init(provider="langfuse")
            
            # Disable auto-instrumentation for manual control
            obs.init(auto_instrument=False)
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
        
        result = self._provider.init(**kwargs)
        
        # Auto-instrument Agent classes after successful init
        if result and auto_instrument:
            self._auto_instrument_agents()
        
        return result
    
    # Mapping from obs provider names to litellm callback names
    _LITELLM_CALLBACK_MAP = {
        "langsmith": "langsmith",
        "langfuse": "langfuse",
        "datadog": "datadog",
        "opik": "opik",
        "braintrust": "braintrust",
        "mlflow": "mlflow",
        "langwatch": "langwatch",
    }
    
    def _get_litellm_callback_name(self, provider_name: str) -> Optional[str]:
        """Get the litellm callback name for a provider."""
        return self._LITELLM_CALLBACK_MAP.get(provider_name)
    
    def _auto_instrument_agents(self) -> None:
        """
        Auto-instrument Agent/Agents/Workflow classes to create spans automatically.
        
        This patches the main lifecycle methods (chat, start, run, astart) to
        create traces and spans without requiring explicit obs.trace() wrappers.
        Also sets litellm callbacks for providers that support it, and registers
        the ObservabilitySink bridge for ContextTraceEmitter events.
        """
        if not self._provider or not self._provider._initialized:
            return
        
        try:
            # Set litellm callbacks for the active provider
            self._setup_litellm_callbacks()
            
            # Register bridge sink for ContextTraceEmitter events
            self._setup_bridge_sink()
            
            from functools import wraps
            
            # Try to import praisonaiagents classes
            try:
                from praisonaiagents.agent.agent import Agent
                self._wrap_agent_class(Agent)
            except ImportError:
                pass
            
            try:
                from praisonaiagents.agents.agents import Agents
                self._wrap_workflow_class(Agents)
            except ImportError:
                pass
                
        except Exception:
            # Silently fail - don't break user code if instrumentation fails
            pass
    
    def _setup_litellm_callbacks(self) -> None:
        """Set litellm callbacks for the active provider."""
        provider_name = self._provider.name if self._provider else None
        if not provider_name:
            return
        
        callback_name = self._get_litellm_callback_name(provider_name)
        if not callback_name:
            return
        
        try:
            import litellm
            
            # Add callback if not already present
            if not hasattr(litellm, 'callbacks') or litellm.callbacks is None:
                litellm.callbacks = []
            if callback_name not in litellm.callbacks:
                litellm.callbacks.append(callback_name)
            
            if not hasattr(litellm, 'success_callback') or litellm.success_callback is None:
                litellm.success_callback = []
            if callback_name not in litellm.success_callback:
                litellm.success_callback.append(callback_name)
        except ImportError:
            pass
    
    def _setup_bridge_sink(self) -> None:
        """Register ObservabilitySink as the ContextTraceEmitter sink."""
        try:
            from praisonai_tools.observability.bridge import ObservabilitySink
            from praisonaiagents.trace.context_events import (
                ContextTraceEmitter,
                set_context_emitter,
            )
            
            sink = ObservabilitySink(self)
            emitter = ContextTraceEmitter(
                sink=sink,
                session_id=self.config.session_id or "",
                enabled=True,
            )
            set_context_emitter(emitter)
        except ImportError:
            pass
    
    def _wrap_agent_class(self, agent_cls: type) -> None:
        """Wrap Agent class methods to auto-create spans with input/output data."""
        from functools import wraps
        import json
        
        # Skip if already instrumented
        if getattr(agent_cls, '_obs_instrumented', False):
            return
        
        manager = self
        
        def _extract_chat_input(agent_self, args, kwargs):
            """Extract the input prompt from chat() arguments."""
            prompt = args[0] if args else kwargs.get('prompt', kwargs.get('message', ''))
            agent_name = getattr(agent_self, 'name', 'unknown')
            instructions = getattr(agent_self, 'instructions', '')
            model = getattr(agent_self, 'model', None)
            # Use a dict format that LangSmith can display
            input_data = {"input": str(prompt) if prompt else ""}
            if instructions:
                input_data["instructions"] = str(instructions)
            if agent_name:
                input_data["agent_name"] = agent_name
            if model:
                input_data["model"] = str(model)
            return input_data
        
        def _set_span_io(span, input_data, output_data):
            """Set input/output attributes on a span for LangSmith display."""
            if span is None:
                return
            try:
                # LangSmith recognizes these attributes for chain/agent spans
                if input_data:
                    input_str = json.dumps(input_data) if isinstance(input_data, dict) else str(input_data)
                    span.attributes["input.value"] = input_str
                    span.attributes["input"] = input_str
                if output_data:
                    output_str = str(output_data) if not isinstance(output_data, str) else output_data
                    span.attributes["output.value"] = output_str
                    span.attributes["output"] = output_str
            except Exception:
                pass
        
        # Wrap chat method
        if hasattr(agent_cls, 'chat'):
            original_chat = agent_cls.chat
            
            @wraps(original_chat)
            def instrumented_chat(self, *args, **kwargs):
                agent_name = getattr(self, 'name', 'unknown')
                input_data = _extract_chat_input(self, args, kwargs)
                with manager.trace(agent_name):
                    span = manager.start_span(agent_name, kind=SpanKind.AGENT)
                    try:
                        # Set input before the call
                        _set_span_io(span, input_data, None)
                        result = original_chat(self, *args, **kwargs)
                        # Set output after the call
                        output_str = str(result) if result else ""
                        # Truncate very long outputs for span attributes
                        if len(output_str) > 4000:
                            output_str = output_str[:4000] + "..."
                        _set_span_io(span, None, output_str)
                        return result
                    except Exception as e:
                        if span:
                            span.set_error(e)
                        raise
                    finally:
                        manager.end_span(span)
            
            agent_cls.chat = instrumented_chat
        
        # Wrap start method
        if hasattr(agent_cls, 'start'):
            original_start = agent_cls.start
            
            @wraps(original_start)
            def instrumented_start(self, *args, **kwargs):
                import types
                agent_name = getattr(self, 'name', 'unknown')
                
                result = original_start(self, *args, **kwargs)
                
                # Handle generator (streaming) mode
                if isinstance(result, types.GeneratorType):
                    def traced_generator():
                        with manager.trace(agent_name):
                            with manager.span(agent_name, kind=SpanKind.AGENT):
                                for chunk in result:
                                    yield chunk
                    return traced_generator()
                else:
                    return result
            
            agent_cls.start = instrumented_start
        
        # Wrap run method
        if hasattr(agent_cls, 'run'):
            original_run = agent_cls.run
            
            @wraps(original_run)
            def instrumented_run(self, *args, **kwargs):
                agent_name = getattr(self, 'name', 'unknown')
                with manager.trace(agent_name):
                    with manager.span(agent_name, kind=SpanKind.AGENT):
                        return original_run(self, *args, **kwargs)
            
            agent_cls.run = instrumented_run
        
        # Mark as instrumented
        agent_cls._obs_instrumented = True
    
    def _wrap_workflow_class(self, workflow_cls: type) -> None:
        """Wrap Agents (workflow) class methods to auto-create spans."""
        from functools import wraps
        
        # Skip if already instrumented
        if getattr(workflow_cls, '_obs_instrumented', False):
            return
        
        manager = self
        
        # Wrap start method
        if hasattr(workflow_cls, 'start'):
            original_start = workflow_cls.start
            
            @wraps(original_start)
            def instrumented_start(self, *args, **kwargs):
                workflow_name = getattr(self, 'name', None) or 'workflow'
                with manager.trace(f"workflow.{workflow_name}"):
                    with manager.span(f"workflow.{workflow_name}.start", kind=SpanKind.WORKFLOW):
                        return original_start(self, *args, **kwargs)
            
            workflow_cls.start = instrumented_start
        
        # Wrap astart (async) method
        if hasattr(workflow_cls, 'astart'):
            original_astart = workflow_cls.astart
            
            @wraps(original_astart)
            async def instrumented_astart(self, *args, **kwargs):
                workflow_name = getattr(self, 'name', None) or 'workflow'
                with manager.trace(f"workflow.{workflow_name}"):
                    with manager.span(f"workflow.{workflow_name}.astart", kind=SpanKind.WORKFLOW):
                        return await original_astart(self, *args, **kwargs)
            
            workflow_cls.astart = instrumented_astart
        
        # Mark as instrumented
        workflow_cls._obs_instrumented = True
    
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
