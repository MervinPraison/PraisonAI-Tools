"""
LangSmith Provider

Integration with LangSmith for LLM observability.
https://smith.langchain.com/
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


class LangSmithProvider(BaseObservabilityProvider):
    """LangSmith observability provider using OpenTelemetry."""
    
    name = "langsmith"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize LangSmith provider."""
        super().__init__(config)
        self._tracer_provider = None
        self._tracer = None
    
    def is_available(self) -> bool:
        """Check if required SDKs are available."""
        try:
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            return True
        except ImportError:
            return False
    
    def init(self, **kwargs) -> bool:
        """Initialize LangSmith via OpenTelemetry."""
        if not self.is_available():
            return False
        
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            
            api_key = kwargs.get("api_key") or os.getenv("LANGSMITH_API_KEY")
            project = kwargs.get("project") or os.getenv("LANGSMITH_PROJECT", "default")
            endpoint = kwargs.get("endpoint") or os.getenv(
                "LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"
            )
            
            if not api_key:
                return False
            
            # Configure OTLP endpoint for LangSmith
            otlp_endpoint = f"{endpoint}/otel/v1/traces"
            headers = {
                "x-api-key": api_key,
                "Langsmith-Project": project,
            }
            
            # Setup tracer provider
            self._tracer_provider = TracerProvider()
            self._tracer_provider.add_span_processor(
                SimpleSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, headers=headers))
            )
            trace.set_tracer_provider(self._tracer_provider)
            self._tracer = trace.get_tracer("praisonai")
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"LangSmith init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown LangSmith provider."""
        if self._tracer_provider:
            try:
                self._tracer_provider.shutdown()
            except Exception:
                pass
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check LangSmith connection."""
        if not self._initialized:
            return False, "LangSmith not initialized"
        
        api_key = os.getenv("LANGSMITH_API_KEY")
        if api_key:
            return True, "LangSmith API key configured"
        return False, "LANGSMITH_API_KEY not set"
    
    # Map SpanKind to LangSmith span kind values
    _LANGSMITH_SPAN_KINDS = {
        "llm": "llm",
        "tool": "tool",
        "agent": "chain",
        "chain": "chain",
        "workflow": "chain",
        "retrieval": "retriever",
        "custom": "chain",
    }
    
    def export_span(self, span: Span) -> bool:
        """Export span to LangSmith via OTel with GenAI semantic conventions."""
        if not self._initialized or not self._tracer:
            return False
        
        try:
            with self._tracer.start_as_current_span(span.name) as otel_span:
                # LangSmith-specific span kind
                ls_kind = self._LANGSMITH_SPAN_KINDS.get(span.kind.value, "chain")
                otel_span.set_attribute("langsmith.span.kind", ls_kind)
                
                # GenAI model attributes
                if span.model:
                    otel_span.set_attribute("gen_ai.request.model", span.model)
                    otel_span.set_attribute("gen_ai.response.model", span.model)
                    otel_span.set_attribute("gen_ai.system", "openai")
                
                # GenAI usage metrics
                if span.input_tokens:
                    otel_span.set_attribute("gen_ai.usage.prompt_tokens", span.input_tokens)
                if span.output_tokens:
                    otel_span.set_attribute("gen_ai.usage.completion_tokens", span.output_tokens)
                if span.input_tokens or span.output_tokens:
                    otel_span.set_attribute(
                        "gen_ai.usage.total_tokens",
                        (span.input_tokens or 0) + (span.output_tokens or 0),
                    )
                
                # Tool attributes
                if span.tool_name:
                    otel_span.set_attribute("gen_ai.tool.name", span.tool_name)
                    otel_span.set_attribute("tool.name", span.tool_name)
                
                # Forward all custom attributes (includes gen_ai.prompt.*, gen_ai.completion.*, etc.)
                for key, value in span.attributes.items():
                    try:
                        otel_span.set_attribute(key, str(value))
                    except Exception:
                        pass
                
                if span.error_message:
                    from opentelemetry.trace import Status, StatusCode
                    otel_span.set_status(Status(StatusCode.ERROR, span.error_message))
            
            return True
        except Exception:
            return False
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to LangSmith."""
        if not self._initialized:
            return False
        return True


# Auto-register provider
ObservabilityManager.register_provider("langsmith", LangSmithProvider)
