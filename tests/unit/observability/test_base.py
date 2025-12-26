"""Tests for base observability classes."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from praisonai_tools.observability.base import (
    BaseObservabilityProvider,
    Span,
    SpanContext,
    SpanKind,
    SpanStatus,
    Trace,
)
from praisonai_tools.observability.config import ObservabilityConfig


class TestSpanContext:
    """Tests for SpanContext."""
    
    def test_new_without_parent(self):
        """Test creating new context without parent."""
        ctx = SpanContext.new()
        assert ctx.trace_id is not None
        assert ctx.span_id is not None
        assert ctx.parent_span_id is None
    
    def test_new_with_parent(self):
        """Test creating new context with parent."""
        parent = SpanContext.new()
        child = SpanContext.new(parent)
        assert child.trace_id == parent.trace_id
        assert child.span_id != parent.span_id
        assert child.parent_span_id == parent.span_id


class TestSpan:
    """Tests for Span."""
    
    def test_span_creation(self):
        """Test span creation."""
        ctx = SpanContext.new()
        span = Span(name="test", kind=SpanKind.LLM, context=ctx)
        assert span.name == "test"
        assert span.kind == SpanKind.LLM
        assert span.status == SpanStatus.UNSET
        assert span.start_time is not None
    
    def test_span_end(self):
        """Test ending a span."""
        ctx = SpanContext.new()
        span = Span(name="test", kind=SpanKind.TOOL, context=ctx)
        span.end(SpanStatus.OK)
        assert span.end_time is not None
        assert span.status == SpanStatus.OK
    
    def test_span_set_error(self):
        """Test setting error on span."""
        ctx = SpanContext.new()
        span = Span(name="test", kind=SpanKind.AGENT, context=ctx)
        span.set_error(ValueError("test error"))
        assert span.status == SpanStatus.ERROR
        assert span.error_message == "test error"
        assert span.error_type == "ValueError"
    
    def test_span_add_event(self):
        """Test adding event to span."""
        ctx = SpanContext.new()
        span = Span(name="test", kind=SpanKind.CUSTOM, context=ctx)
        span.add_event("test_event", {"key": "value"})
        assert len(span.events) == 1
        assert span.events[0]["name"] == "test_event"
    
    def test_span_duration(self):
        """Test span duration calculation."""
        ctx = SpanContext.new()
        span = Span(name="test", kind=SpanKind.LLM, context=ctx)
        assert span.duration_ms is None
        span.end()
        assert span.duration_ms is not None
        assert span.duration_ms >= 0
    
    def test_span_to_dict(self):
        """Test span serialization."""
        ctx = SpanContext.new()
        span = Span(
            name="test",
            kind=SpanKind.LLM,
            context=ctx,
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
        )
        span.end()
        data = span.to_dict()
        assert data["name"] == "test"
        assert data["kind"] == "llm"
        assert data["model"] == "gpt-4"
        assert data["input_tokens"] == 100
        assert data["output_tokens"] == 50


class TestTrace:
    """Tests for Trace."""
    
    def test_trace_creation(self):
        """Test trace creation."""
        trace = Trace(trace_id="test-123", name="test-trace")
        assert trace.trace_id == "test-123"
        assert trace.name == "test-trace"
        assert len(trace.spans) == 0
    
    def test_trace_add_span(self):
        """Test adding span to trace."""
        trace = Trace(trace_id="test-123", name="test-trace")
        ctx = SpanContext(trace_id="test-123", span_id="span-1")
        span = Span(name="test-span", kind=SpanKind.LLM, context=ctx)
        trace.add_span(span)
        assert len(trace.spans) == 1
    
    def test_trace_end(self):
        """Test ending a trace."""
        trace = Trace(trace_id="test-123", name="test-trace")
        trace.end()
        assert trace.end_time is not None
    
    def test_trace_to_dict(self):
        """Test trace serialization."""
        trace = Trace(
            trace_id="test-123",
            name="test-trace",
            session_id="session-1",
            user_id="user-1",
        )
        trace.end()
        data = trace.to_dict()
        assert data["trace_id"] == "test-123"
        assert data["name"] == "test-trace"
        assert data["session_id"] == "session-1"


class TestObservabilityConfig:
    """Tests for ObservabilityConfig."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = ObservabilityConfig()
        assert config.enabled is True
        assert config.trace_llm_calls is True
        assert config.trace_tool_calls is True
        assert config.batch_size == 100
    
    def test_config_from_env(self):
        """Test config from environment variables."""
        with patch.dict("os.environ", {
            "PRAISONAI_OBS_PROVIDER": "langfuse",
            "PRAISONAI_OBS_PROJECT": "test-project",
            "PRAISONAI_OBS_ENABLED": "false",
        }):
            config = ObservabilityConfig.from_env()
            assert config.provider == "langfuse"
            assert config.project_name == "test-project"
            assert config.enabled is False
    
    def test_config_merge(self):
        """Test config merge."""
        config = ObservabilityConfig(provider="langfuse")
        merged = config.merge(project_name="new-project", session_id="sess-1")
        assert merged.provider == "langfuse"
        assert merged.project_name == "new-project"
        assert merged.session_id == "sess-1"


class ConcreteProvider(BaseObservabilityProvider):
    """Concrete implementation for testing."""
    
    name = "test"
    
    def init(self, **kwargs):
        self._initialized = True
        return True
    
    def shutdown(self):
        self._initialized = False
    
    def is_available(self):
        return True
    
    def check_connection(self):
        return True, "OK"
    
    def export_span(self, span):
        return True
    
    def export_trace(self, trace):
        return True


class TestBaseObservabilityProvider:
    """Tests for BaseObservabilityProvider."""
    
    def test_provider_init(self):
        """Test provider initialization."""
        provider = ConcreteProvider()
        assert provider.init() is True
        assert provider._initialized is True
    
    def test_provider_start_trace(self):
        """Test starting a trace."""
        provider = ConcreteProvider()
        provider.init()
        trace = provider.start_trace("test-trace", session_id="sess-1")
        assert trace is not None
        assert trace.name == "test-trace"
        assert trace.session_id == "sess-1"
    
    def test_provider_start_span(self):
        """Test starting a span."""
        provider = ConcreteProvider()
        provider.init()
        provider.start_trace("test-trace")
        span = provider.start_span("test-span", SpanKind.LLM)
        assert span is not None
        assert span.name == "test-span"
        assert span.kind == SpanKind.LLM
    
    def test_provider_trace_context_manager(self):
        """Test trace context manager."""
        provider = ConcreteProvider()
        provider.init()
        with provider.trace("test-trace") as trace:
            assert trace is not None
            assert trace.name == "test-trace"
    
    def test_provider_span_context_manager(self):
        """Test span context manager."""
        provider = ConcreteProvider()
        provider.init()
        with provider.span("test-span", SpanKind.TOOL) as span:
            assert span is not None
            assert span.name == "test-span"
    
    def test_provider_log_llm_call(self):
        """Test logging LLM call."""
        provider = ConcreteProvider()
        provider.init()
        provider.start_trace("test")
        span = provider.log_llm_call(
            model="gpt-4",
            input_messages="Hello",
            output="Hi there",
            input_tokens=10,
            output_tokens=5,
        )
        assert span is not None
        assert span.model == "gpt-4"
        assert span.input_tokens == 10
    
    def test_provider_log_tool_call(self):
        """Test logging tool call."""
        provider = ConcreteProvider()
        provider.init()
        provider.start_trace("test")
        span = provider.log_tool_call(
            tool_name="search",
            tool_input={"query": "test"},
            tool_output={"results": []},
        )
        assert span is not None
        assert span.tool_name == "search"
    
    def test_provider_decorator(self):
        """Test function decorator."""
        provider = ConcreteProvider()
        provider.init()
        provider.start_trace("test")
        
        @provider.decorator("decorated-func", SpanKind.CUSTOM)
        def my_func():
            return "result"
        
        result = my_func()
        assert result == "result"
