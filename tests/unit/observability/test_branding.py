"""
Tests for PraisonAI observability branding.

Verifies:
- Tracer name is 'praisonai.observability'
- Spans carry praisonai.version and praisonai.framework attributes
- Workflow span names are simplified
"""

import pytest
from unittest.mock import MagicMock, patch


class TestTracerName:
    """Verify providers use the branded tracer name."""

    def test_langsmith_tracer_name(self):
        """LangSmith provider should use 'praisonai.observability' tracer name."""
        import inspect
        from praisonai_tools.observability.providers.langsmith_provider import LangSmithProvider
        source = inspect.getsource(LangSmithProvider.init)
        assert 'get_tracer("praisonai.observability")' in source

    def test_langfuse_tracer_name(self):
        """Langfuse provider should use 'praisonai.observability' tracer name."""
        import inspect
        from praisonai_tools.observability.providers.langfuse_provider import LangfuseProvider
        source = inspect.getsource(LangfuseProvider.init)
        assert 'get_tracer("praisonai.observability")' in source


class TestBrandingAttributes:
    """Verify branding attributes are set on spans."""

    def _make_manager(self):
        """Create a minimally-configured ObservabilityManager for testing."""
        from praisonai_tools.observability.manager import ObservabilityManager

        manager = ObservabilityManager.__new__(ObservabilityManager)
        manager._provider = None
        manager._providers = {}
        manager._initialized = False
        manager.config = MagicMock()
        return manager

    def test_branding_attrs_set_on_agent_span(self):
        """Agent spans should carry praisonai.version and praisonai.framework."""
        from praisonai_tools.observability.base import SpanKind

        manager = self._make_manager()

        mock_span = MagicMock()
        mock_span.attributes = {}
        mock_span.set_error = MagicMock()

        def mock_start_span(name, kind=None, **kwargs):
            mock_span.name = name
            return mock_span

        manager.start_span = mock_start_span
        manager.end_span = MagicMock()
        manager.trace = MagicMock(
            return_value=MagicMock(
                __enter__=MagicMock(),
                __exit__=MagicMock(return_value=False),
            )
        )

        class MockAgent:
            name = "TestAgent"
            instructions = "test"
            model = "gpt-4o-mini"
            role = "tester"
            goal = "test"

            def chat(self, prompt, *args, **kwargs):
                return "test response"

        manager._wrap_agent_class(MockAgent)
        agent = MockAgent()
        agent.chat("hello")

        assert "praisonai.version" in mock_span.attributes
        assert mock_span.attributes["praisonai.framework"] == "praisonai"

    def test_workflow_span_name_simplified(self):
        """Workflow spans should use clean names, not prefixed ones."""
        manager = self._make_manager()

        created_span_names = []
        created_trace_names = []

        mock_span = MagicMock()
        mock_span.attributes = {}

        class MockSpanCtx:
            def __enter__(self_ctx):
                return mock_span
            def __exit__(self_ctx, *args):
                return False

        def mock_span_fn(name, kind=None, **kwargs):
            created_span_names.append(name)
            return MockSpanCtx()

        manager.span = mock_span_fn
        manager.trace = lambda name: MagicMock(
            __enter__=lambda s: (created_trace_names.append(name), s)[-1],
            __exit__=MagicMock(return_value=False),
        )

        class MockWorkflow:
            name = "MyTeam"

            def start(self, *args, **kwargs):
                return "done"

        manager._wrap_workflow_class(MockWorkflow)
        wf = MockWorkflow()
        wf.start()

        # Should be "MyTeam", NOT "workflow.MyTeam.start"
        assert created_span_names == ["MyTeam"]
        assert created_trace_names == ["MyTeam"]
        assert mock_span.attributes.get("praisonai.framework") == "praisonai"
        assert "praisonai.version" in mock_span.attributes
