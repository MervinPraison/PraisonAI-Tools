"""Tests for ObservabilityManager."""

from unittest.mock import patch, MagicMock

from praisonai_tools.observability.manager import ObservabilityManager, _NoOpContextManager
from praisonai_tools.observability.config import ObservabilityConfig
from praisonai_tools.observability.base import BaseObservabilityProvider, SpanKind


class MockProvider(BaseObservabilityProvider):
    """Mock provider for testing."""
    
    name = "mock"
    
    def init(self, **kwargs):
        self._initialized = True
        return True
    
    def shutdown(self):
        self._initialized = False
    
    def is_available(self):
        return True
    
    def check_connection(self):
        return True, "Mock connection OK"
    
    def export_span(self, span):
        return True
    
    def export_trace(self, trace):
        return True


class TestObservabilityManager:
    """Tests for ObservabilityManager."""
    
    def setup_method(self):
        """Reset singleton before each test."""
        ObservabilityManager._instance = None
        ObservabilityManager._providers = {}
    
    def test_singleton_pattern(self):
        """Test that manager is a singleton."""
        mgr1 = ObservabilityManager()
        mgr2 = ObservabilityManager()
        assert mgr1 is mgr2
    
    def test_register_provider(self):
        """Test provider registration."""
        ObservabilityManager.register_provider("mock", MockProvider)
        assert "mock" in ObservabilityManager.list_providers()
    
    def test_list_providers(self):
        """Test listing providers."""
        ObservabilityManager.register_provider("mock1", MockProvider)
        ObservabilityManager.register_provider("mock2", MockProvider)
        providers = ObservabilityManager.list_providers()
        assert "mock1" in providers
        assert "mock2" in providers
    
    def test_init_with_provider(self):
        """Test initialization with specific provider."""
        ObservabilityManager.register_provider("mock", MockProvider)
        mgr = ObservabilityManager()
        
        with patch.dict("os.environ", {"MOCK_API_KEY": "test"}):
            result = mgr.init(provider="mock")
            assert result is True
            assert mgr.enabled is True
    
    def test_init_without_provider(self):
        """Test initialization without provider returns False."""
        mgr = ObservabilityManager()
        result = mgr.init()
        assert result is False
        assert mgr.enabled is False
    
    def test_shutdown(self):
        """Test shutdown."""
        ObservabilityManager.register_provider("mock", MockProvider)
        mgr = ObservabilityManager()
        mgr.init(provider="mock")
        mgr.shutdown()
        assert mgr._provider is None
    
    def test_doctor(self):
        """Test doctor diagnostics."""
        ObservabilityManager.register_provider("mock", MockProvider)
        mgr = ObservabilityManager()
        mgr.init(provider="mock")
        
        results = mgr.doctor()
        assert results["enabled"] is True
        assert results["provider"] == "mock"
        assert results["connection_status"] is True
    
    def test_trace_context_manager_enabled(self):
        """Test trace context manager when enabled."""
        ObservabilityManager.register_provider("mock", MockProvider)
        mgr = ObservabilityManager()
        mgr.init(provider="mock")
        
        with mgr.trace("test-trace") as trace:
            assert trace is not None
    
    def test_trace_context_manager_disabled(self):
        """Test trace context manager when disabled."""
        mgr = ObservabilityManager()
        
        with mgr.trace("test-trace") as trace:
            assert trace is None
    
    def test_span_context_manager_enabled(self):
        """Test span context manager when enabled."""
        ObservabilityManager.register_provider("mock", MockProvider)
        mgr = ObservabilityManager()
        mgr.init(provider="mock")
        mgr.start_trace("test")
        
        with mgr.span("test-span", SpanKind.LLM) as span:
            assert span is not None
    
    def test_span_context_manager_disabled(self):
        """Test span context manager when disabled."""
        mgr = ObservabilityManager()
        
        with mgr.span("test-span") as span:
            assert span is None
    
    def test_log_llm_call_enabled(self):
        """Test log_llm_call when enabled."""
        ObservabilityManager.register_provider("mock", MockProvider)
        mgr = ObservabilityManager()
        mgr.init(provider="mock")
        mgr.start_trace("test")
        
        span = mgr.log_llm_call("gpt-4", "input", "output")
        assert span is not None
    
    def test_log_llm_call_disabled(self):
        """Test log_llm_call when disabled."""
        mgr = ObservabilityManager()
        span = mgr.log_llm_call("gpt-4", "input", "output")
        assert span is None
    
    def test_decorator_enabled(self):
        """Test decorator when enabled."""
        ObservabilityManager.register_provider("mock", MockProvider)
        mgr = ObservabilityManager()
        mgr.init(provider="mock")
        mgr.start_trace("test")
        
        @mgr.decorator("test-func")
        def my_func():
            return 42
        
        result = my_func()
        assert result == 42
    
    def test_decorator_disabled(self):
        """Test decorator when disabled (no-op)."""
        mgr = ObservabilityManager()
        
        @mgr.decorator("test-func")
        def my_func():
            return 42
        
        result = my_func()
        assert result == 42


class TestNoOpContextManager:
    """Tests for _NoOpContextManager."""
    
    def test_enter_returns_none(self):
        """Test that __enter__ returns None."""
        cm = _NoOpContextManager()
        result = cm.__enter__()
        assert result is None
    
    def test_exit_does_nothing(self):
        """Test that __exit__ does nothing."""
        cm = _NoOpContextManager()
        cm.__exit__(None, None, None)  # Should not raise
