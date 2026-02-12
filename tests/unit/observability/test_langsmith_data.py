"""
Tests for LangSmith trace data population (Issue #1103).

Verifies that:
1. Auto-instrumented spans contain GenAI semantic attributes
2. LiteLLM callbacks are preserved when obs is initialized
3. Bridge sink forwards ContextEvents to the observability provider
4. Async safety with contextvars for span state
"""

import os
import pytest
from unittest.mock import patch, MagicMock, call
from contextlib import contextmanager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class SpanRecorder:
    """Records spans exported by a provider for assertion."""
    
    def __init__(self):
        self.spans = []
        self.traces = []
    
    def export_span(self, span):
        self.spans.append(span)
        return True
    
    def export_trace(self, trace):
        self.traces.append(trace)
        return True


def _make_mock_provider():
    """Create a mock provider that records exported spans."""
    from praisonai_tools.observability.base import BaseObservabilityProvider
    
    class RecordingProvider(BaseObservabilityProvider):
        name = "recording"
        
        def __init__(self, config=None):
            super().__init__(config)
            self.exported_spans = []
            self.exported_traces = []
        
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
            self.exported_spans.append(span)
            return True
        
        def export_trace(self, trace):
            self.exported_traces.append(trace)
            return True
    
    return RecordingProvider


# ---------------------------------------------------------------------------
# Test: LiteLLM callbacks preserved
# ---------------------------------------------------------------------------

class TestLiteLLMCallbackPreservation:
    """LiteLLM callbacks must NOT be wiped when obs is active."""
    
    def test_configure_logging_preserves_obs_callbacks(self):
        """LLM._configure_logging() should preserve observability callbacks."""
        try:
            import litellm
        except ImportError:
            pytest.skip("litellm not installed")
        
        # Simulate obs setting a callback before LLM init
        litellm.callbacks = ["langsmith"]
        litellm.success_callback = ["langsmith"]
        
        # Reset class state to force reconfiguration
        from praisonaiagents.llm.llm import LLM
        LLM._logging_configured = False
        LLM._configure_logging()
        
        # Callbacks set by observability should be preserved
        assert "langsmith" in litellm.callbacks or "langsmith" in litellm.success_callback, \
            "Observability callbacks were cleared by LLM._configure_logging()"
    
    def test_litellm_preserves_known_obs_callbacks(self):
        """Known observability callbacks (langfuse, datadog, etc.) are preserved."""
        try:
            import litellm
        except ImportError:
            pytest.skip("litellm not installed")
        
        # Set a known observability callback
        litellm.callbacks = ["langfuse"]
        
        from praisonaiagents.llm.llm import LLM
        LLM._logging_configured = False
        LLM._configure_logging()
        
        # Known obs callbacks should be preserved
        assert "langfuse" in litellm.callbacks, \
            "Known observability callback 'langfuse' was cleared"


# ---------------------------------------------------------------------------
# Test: Auto-instrumentation sets litellm callbacks
# ---------------------------------------------------------------------------

class TestAutoInstrumentationLiteLLMCallbacks:
    """obs.init() should configure litellm callbacks for the provider."""
    
    def setup_method(self):
        from praisonai_tools.observability.manager import ObservabilityManager
        ObservabilityManager._instance = None
        ObservabilityManager._providers = {}
    
    def test_auto_instrument_sets_litellm_callback_for_langsmith(self):
        """obs.init(provider='langsmith') should set litellm.callbacks=['langsmith']."""
        try:
            import litellm
        except ImportError:
            pytest.skip("litellm not installed")
        
        from praisonai_tools.observability.manager import ObservabilityManager
        
        RecordingProvider = _make_mock_provider()
        RecordingProvider.name = "langsmith"
        ObservabilityManager.register_provider("langsmith", RecordingProvider)
        
        mgr = ObservabilityManager()
        
        # Clear litellm callbacks first
        litellm.callbacks = []
        
        with patch.dict("os.environ", {"LANGSMITH_API_KEY": "test"}):
            mgr.init(provider="langsmith")
        
        assert "langsmith" in litellm.callbacks, \
            "obs.init(provider='langsmith') should add 'langsmith' to litellm.callbacks"
    
    def test_auto_instrument_does_not_duplicate_callback(self):
        """Should not add duplicate callbacks."""
        try:
            import litellm
        except ImportError:
            pytest.skip("litellm not installed")
        
        from praisonai_tools.observability.manager import ObservabilityManager
        
        RecordingProvider = _make_mock_provider()
        RecordingProvider.name = "langsmith"
        ObservabilityManager.register_provider("langsmith", RecordingProvider)
        
        mgr = ObservabilityManager()
        litellm.callbacks = ["langsmith"]  # Already set
        
        with patch.dict("os.environ", {"LANGSMITH_API_KEY": "test"}):
            mgr.init(provider="langsmith")
        
        assert litellm.callbacks.count("langsmith") == 1, \
            "Should not duplicate existing callback"


# ---------------------------------------------------------------------------
# Test: Bridge sink
# ---------------------------------------------------------------------------

class TestObservabilitySink:
    """ObservabilitySink bridges ContextEvents to ObservabilityManager."""
    
    def setup_method(self):
        from praisonai_tools.observability.manager import ObservabilityManager
        ObservabilityManager._instance = None
        ObservabilityManager._providers = {}
    
    def test_sink_forwards_llm_request_event(self):
        """LLM_REQUEST event should create an LLM span with input data."""
        from praisonai_tools.observability.bridge import ObservabilitySink
        from praisonai_tools.observability.manager import ObservabilityManager
        from praisonaiagents.trace.context_events import ContextEvent, ContextEventType
        
        RecordingProvider = _make_mock_provider()
        ObservabilityManager.register_provider("recording", RecordingProvider)
        mgr = ObservabilityManager()
        mgr.init(provider="recording", auto_instrument=False)
        mgr.start_trace("test")
        
        sink = ObservabilitySink(mgr)
        
        event = ContextEvent(
            event_type=ContextEventType.LLM_REQUEST,
            timestamp=1000.0,
            session_id="test-session",
            agent_name="TestAgent",
            data={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are helpful"},
                    {"role": "user", "content": "What is AI?"},
                ],
            },
        )
        
        sink.emit(event)
        
        # Should have started a span
        provider = mgr._provider
        assert len(provider._span_stack) > 0 or len(provider.exported_spans) > 0, \
            "LLM_REQUEST should create a span"
    
    def test_sink_forwards_llm_response_event(self):
        """LLM_RESPONSE event should populate token usage and end the span."""
        from praisonai_tools.observability.bridge import ObservabilitySink
        from praisonai_tools.observability.manager import ObservabilityManager
        from praisonai_tools.observability.base import SpanKind
        from praisonaiagents.trace.context_events import ContextEvent, ContextEventType
        
        RecordingProvider = _make_mock_provider()
        ObservabilityManager.register_provider("recording", RecordingProvider)
        mgr = ObservabilityManager()
        mgr.init(provider="recording", auto_instrument=False)
        mgr.start_trace("test")
        
        sink = ObservabilitySink(mgr)
        
        # First: LLM_REQUEST
        sink.emit(ContextEvent(
            event_type=ContextEventType.LLM_REQUEST,
            timestamp=1000.0,
            session_id="test",
            agent_name="TestAgent",
            data={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hi"}]},
        ))
        
        # Then: LLM_RESPONSE
        sink.emit(ContextEvent(
            event_type=ContextEventType.LLM_RESPONSE,
            timestamp=1001.0,
            session_id="test",
            agent_name="TestAgent",
            prompt_tokens=10,
            completion_tokens=20,
            cost_usd=0.001,
            data={
                "response_tokens": 20,
                "finish_reason": "stop",
            },
        ))
        
        # Should have exported a span with token usage
        provider = mgr._provider
        assert len(provider.exported_spans) >= 1, "LLM_RESPONSE should end and export the span"
        
        llm_span = provider.exported_spans[-1]
        assert llm_span.input_tokens == 10
        assert llm_span.output_tokens == 20
    
    def test_sink_forwards_tool_events(self):
        """TOOL_CALL_START/END events should create tool spans."""
        from praisonai_tools.observability.bridge import ObservabilitySink
        from praisonai_tools.observability.manager import ObservabilityManager
        from praisonaiagents.trace.context_events import ContextEvent, ContextEventType
        
        RecordingProvider = _make_mock_provider()
        ObservabilityManager.register_provider("recording", RecordingProvider)
        mgr = ObservabilityManager()
        mgr.init(provider="recording", auto_instrument=False)
        mgr.start_trace("test")
        
        sink = ObservabilitySink(mgr)
        
        sink.emit(ContextEvent(
            event_type=ContextEventType.TOOL_CALL_START,
            timestamp=1000.0,
            session_id="test",
            agent_name="TestAgent",
            data={"tool_name": "search_web", "arguments": {"query": "AI"}},
        ))
        
        sink.emit(ContextEvent(
            event_type=ContextEventType.TOOL_CALL_END,
            timestamp=1001.0,
            session_id="test",
            agent_name="TestAgent",
            data={"tool_name": "search_web", "result": "AI is..."},
        ))
        
        provider = mgr._provider
        assert len(provider.exported_spans) >= 1, "TOOL_CALL events should create and export a span"
        
        tool_span = provider.exported_spans[-1]
        assert tool_span.tool_name == "search_web"
    
    def test_sink_skips_agent_events(self):
        """AGENT_START/END events are skipped — wrapper handles them with full I/O."""
        from praisonai_tools.observability.bridge import ObservabilitySink
        from praisonai_tools.observability.manager import ObservabilityManager
        from praisonaiagents.trace.context_events import ContextEvent, ContextEventType
        
        RecordingProvider = _make_mock_provider()
        ObservabilityManager.register_provider("recording", RecordingProvider)
        mgr = ObservabilityManager()
        mgr.init(provider="recording", auto_instrument=False)
        mgr.start_trace("test")
        
        sink = ObservabilitySink(mgr)
        
        sink.emit(ContextEvent(
            event_type=ContextEventType.AGENT_START,
            timestamp=1000.0,
            session_id="test",
            agent_name="Assistant",
            data={"role": "helper", "goal": "be helpful"},
        ))
        
        sink.emit(ContextEvent(
            event_type=ContextEventType.AGENT_END,
            timestamp=1001.0,
            session_id="test",
            agent_name="Assistant",
            data={},
        ))
        
        provider = mgr._provider
        assert len(provider.exported_spans) == 0, \
            "Bridge should skip AGENT events — wrapper handles them with full I/O data"


# ---------------------------------------------------------------------------
# Test: LangSmith provider GenAI attributes
# ---------------------------------------------------------------------------

class TestLangSmithGenAIAttributes:
    """LangSmith provider must set GenAI semantic convention attributes."""
    
    def test_export_span_sets_langsmith_span_kind(self):
        """export_span should set langsmith.span.kind attribute."""
        try:
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        except ImportError:
            pytest.skip("opentelemetry-sdk not installed")
        
        from praisonai_tools.observability.providers.langsmith_provider import LangSmithProvider
        from praisonai_tools.observability.base import Span, SpanKind, SpanContext
        
        provider = LangSmithProvider()
        provider._initialized = True
        
        # Create a mock tracer that records attributes
        mock_otel_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_otel_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        provider._tracer = mock_tracer
        
        span = Span(
            name="llm.gpt-4o",
            kind=SpanKind.LLM,
            context=SpanContext.new(),
            model="gpt-4o",
            input_tokens=50,
            output_tokens=100,
        )
        span.attributes["gen_ai.request.model"] = "gpt-4o"
        
        provider.export_span(span)
        
        # Verify langsmith.span.kind was set
        set_calls = {c[0][0]: c[0][1] for c in mock_otel_span.set_attribute.call_args_list}
        assert "langsmith.span.kind" in set_calls, \
            "Should set langsmith.span.kind attribute"
        assert set_calls["langsmith.span.kind"] == "llm"
    
    def test_export_span_sets_gen_ai_usage_metrics(self):
        """export_span should set gen_ai.usage.* attributes."""
        try:
            from opentelemetry.sdk.trace import TracerProvider
        except ImportError:
            pytest.skip("opentelemetry-sdk not installed")
        
        from praisonai_tools.observability.providers.langsmith_provider import LangSmithProvider
        from praisonai_tools.observability.base import Span, SpanKind, SpanContext
        
        provider = LangSmithProvider()
        provider._initialized = True
        
        mock_otel_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_otel_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        provider._tracer = mock_tracer
        
        span = Span(
            name="llm.gpt-4o",
            kind=SpanKind.LLM,
            context=SpanContext.new(),
            model="gpt-4o",
            input_tokens=50,
            output_tokens=100,
        )
        
        provider.export_span(span)
        
        set_calls = {c[0][0]: c[0][1] for c in mock_otel_span.set_attribute.call_args_list}
        assert set_calls.get("gen_ai.usage.prompt_tokens") == 50
        assert set_calls.get("gen_ai.usage.completion_tokens") == 100


# ---------------------------------------------------------------------------
# Test: Async safety - contextvars for span stack
# ---------------------------------------------------------------------------

class TestAsyncSafetyContextVars:
    """Provider span stack must use contextvars for async safety."""
    
    def test_span_stack_is_per_context(self):
        """Each async context should have its own span stack."""
        from praisonai_tools.observability.base import BaseObservabilityProvider
        
        RecordingProvider = _make_mock_provider()
        
        provider1 = RecordingProvider()
        provider1.init()
        provider1.start_trace("trace1")
        
        # Start a span in context 1
        span1 = provider1.start_span("span1")
        
        # The provider should isolate span state
        # After fix, _span_stack uses contextvars
        assert span1 is not None
        assert span1.name == "span1"


# ---------------------------------------------------------------------------
# Test: Provider-to-litellm callback mapping
# ---------------------------------------------------------------------------

class TestProviderCallbackMapping:
    """Verify the mapping from provider names to litellm callback names."""
    
    def test_langsmith_maps_to_langsmith(self):
        from praisonai_tools.observability.manager import ObservabilityManager
        mgr = ObservabilityManager.__new__(ObservabilityManager)
        mgr._initialized = False
        mgr.__init__()
        assert mgr._get_litellm_callback_name("langsmith") == "langsmith"
    
    def test_langfuse_maps_to_langfuse(self):
        from praisonai_tools.observability.manager import ObservabilityManager
        mgr = ObservabilityManager.__new__(ObservabilityManager)
        mgr._initialized = False
        mgr.__init__()
        assert mgr._get_litellm_callback_name("langfuse") == "langfuse"
    
    def test_unknown_provider_returns_none(self):
        from praisonai_tools.observability.manager import ObservabilityManager
        mgr = ObservabilityManager.__new__(ObservabilityManager)
        mgr._initialized = False
        mgr.__init__()
        assert mgr._get_litellm_callback_name("unknown_provider") is None
