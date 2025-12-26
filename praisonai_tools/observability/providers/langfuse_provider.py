"""
Langfuse Provider

Integration with Langfuse for LLM observability.
https://langfuse.com/
"""

import base64
import os
from typing import Optional

from praisonai_tools.observability.base import (
    BaseObservabilityProvider,
    Span,
    SpanKind,
    Trace,
)
from praisonai_tools.observability.config import ObservabilityConfig
from praisonai_tools.observability.manager import ObservabilityManager


class LangfuseProvider(BaseObservabilityProvider):
    """Langfuse observability provider using OpenTelemetry."""
    
    name = "langfuse"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize Langfuse provider."""
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
        """Initialize Langfuse via OpenTelemetry."""
        if not self.is_available():
            return False
        
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            
            public_key = kwargs.get("public_key") or os.getenv("LANGFUSE_PUBLIC_KEY")
            secret_key = kwargs.get("secret_key") or os.getenv("LANGFUSE_SECRET_KEY")
            host = kwargs.get("host") or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
            
            if not public_key or not secret_key:
                return False
            
            # Create auth header
            auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
            
            # Configure OTLP endpoint
            endpoint = f"{host}/api/public/otel/v1/traces"
            headers = {"Authorization": f"Basic {auth}"}
            
            # Setup tracer provider
            self._tracer_provider = TracerProvider()
            self._tracer_provider.add_span_processor(
                SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint, headers=headers))
            )
            trace.set_tracer_provider(self._tracer_provider)
            self._tracer = trace.get_tracer("praisonai")
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Langfuse init failed: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown Langfuse provider."""
        if self._tracer_provider:
            try:
                self._tracer_provider.shutdown()
            except Exception:
                pass
        self._initialized = False
    
    def check_connection(self) -> tuple:
        """Check Langfuse connection."""
        if not self._initialized:
            return False, "Langfuse not initialized"
        
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        
        if public_key and secret_key:
            return True, "Langfuse credentials configured"
        return False, "LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY not set"
    
    def export_span(self, span: Span) -> bool:
        """Export span to Langfuse via OTel."""
        if not self._initialized or not self._tracer:
            return False
        
        try:
            with self._tracer.start_as_current_span(span.name) as otel_span:
                # Set attributes
                otel_span.set_attribute("span.kind", span.kind.value)
                
                if span.model:
                    otel_span.set_attribute("llm.model", span.model)
                if span.input_tokens:
                    otel_span.set_attribute("llm.input_tokens", span.input_tokens)
                if span.output_tokens:
                    otel_span.set_attribute("llm.output_tokens", span.output_tokens)
                if span.tool_name:
                    otel_span.set_attribute("tool.name", span.tool_name)
                
                for key, value in span.attributes.items():
                    otel_span.set_attribute(key, str(value))
                
                if span.error_message:
                    from opentelemetry.trace import Status, StatusCode
                    otel_span.set_status(
                        Status(StatusCode.ERROR, span.error_message)
                    )
            
            return True
        except Exception:
            return False
    
    def export_trace(self, trace_obj: Trace) -> bool:
        """Export trace to Langfuse."""
        if not self._initialized:
            return False
        
        # Spans are exported individually via OTel
        return True


# Auto-register provider
ObservabilityManager.register_provider("langfuse", LangfuseProvider)
