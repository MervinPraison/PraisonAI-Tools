"""
Observability Bridge

Bridges ContextTraceEmitter events from praisonaiagents core SDK
to the ObservabilityManager's provider (e.g., LangSmith, Langfuse).

This implements the ContextTraceSinkProtocol so the core SDK's
internal trace events (LLM calls, tool calls, agent lifecycle)
are forwarded to external observability providers.

Zero Performance Impact:
- Only active when obs.init() is called
- Lazy imports for praisonaiagents types
- No overhead when not used
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from praisonai_tools.observability.manager import ObservabilityManager


class ObservabilitySink:
    """
    Bridges ContextTraceEmitter events to ObservabilityManager spans.
    
    Implements the ContextTraceSinkProtocol from praisonaiagents.trace.context_events.
    When registered as the active sink, all agent/LLM/tool events are forwarded
    to the configured observability provider.
    """
    
    def __init__(self, manager: "ObservabilityManager"):
        self._manager = manager
        self._active_llm_span = None
        self._active_tool_span = None
        self._active_agent_span = None
    
    def emit(self, event: Any) -> None:
        """
        Receive a ContextEvent and forward to the observability provider.
        
        Args:
            event: A ContextEvent from praisonaiagents.trace.context_events
        """
        try:
            from praisonaiagents.trace.context_events import ContextEventType
        except ImportError:
            return
        
        if not self._manager or not self._manager.enabled:
            return
        
        event_type = event.event_type
        
        # AGENT_START/AGENT_END are handled by _wrap_agent_class in manager.py
        # with full input/output data — skip bridge duplicates to avoid empty spans
        if event_type == ContextEventType.LLM_REQUEST:
            self._handle_llm_request(event)
        elif event_type == ContextEventType.LLM_RESPONSE:
            self._handle_llm_response(event)
        elif event_type == ContextEventType.TOOL_CALL_START:
            self._handle_tool_start(event)
        elif event_type == ContextEventType.TOOL_CALL_END:
            self._handle_tool_end(event)
    
    def _handle_agent_start(self, event: Any) -> None:
        """Create an agent span."""
        from praisonai_tools.observability.base import SpanKind
        
        agent_name = getattr(event, 'agent_name', 'unknown')
        data = getattr(event, 'data', {}) or {}
        
        attrs = {}
        if data.get('role'):
            attrs['agent.role'] = str(data['role'])
        if data.get('goal'):
            attrs['agent.goal'] = str(data['goal'])
        
        span = self._manager.start_span(
            f"agent.{agent_name}",
            kind=SpanKind.AGENT,
            attributes=attrs,
        )
        self._active_agent_span = span
    
    def _handle_agent_end(self, event: Any) -> None:
        """End the agent span."""
        if self._active_agent_span:
            self._manager.end_span(self._active_agent_span)
            self._active_agent_span = None
    
    def _handle_llm_request(self, event: Any) -> None:
        """Create an LLM span with input messages."""
        from praisonai_tools.observability.base import SpanKind
        
        data = getattr(event, 'data', {}) or {}
        model = data.get('model', 'unknown')
        messages = data.get('messages', [])
        
        attrs = {}
        attrs['gen_ai.request.model'] = str(model)
        attrs['gen_ai.system'] = 'openai'
        
        # Set input messages as GenAI prompt attributes
        if messages:
            for i, msg in enumerate(messages):
                if isinstance(msg, dict):
                    role = msg.get('role', '')
                    content = msg.get('content', '')
                    attrs[f'gen_ai.prompt.{i}.role'] = str(role)
                    if content:
                        # Truncate very long content
                        content_str = str(content)
                        if len(content_str) > 10000:
                            content_str = content_str[:10000] + "..."
                        attrs[f'gen_ai.prompt.{i}.content'] = content_str
        
        span = self._manager.start_span(
            str(model),
            kind=SpanKind.LLM,
            attributes=attrs,
        )
        if span:
            span.model = str(model)
        self._active_llm_span = span
    
    def _handle_llm_response(self, event: Any) -> None:
        """Populate LLM span with response data and end it."""
        data = getattr(event, 'data', {}) or {}
        prompt_tokens = getattr(event, 'prompt_tokens', 0) or 0
        completion_tokens = getattr(event, 'completion_tokens', 0) or 0
        cost_usd = getattr(event, 'cost_usd', 0.0) or 0.0
        
        if self._active_llm_span:
            self._active_llm_span.input_tokens = prompt_tokens
            self._active_llm_span.output_tokens = completion_tokens
            self._active_llm_span.total_tokens = prompt_tokens + completion_tokens
            
            # Set GenAI usage attributes
            self._active_llm_span.attributes['gen_ai.usage.prompt_tokens'] = prompt_tokens
            self._active_llm_span.attributes['gen_ai.usage.completion_tokens'] = completion_tokens
            self._active_llm_span.attributes['gen_ai.usage.total_tokens'] = prompt_tokens + completion_tokens
            
            if cost_usd:
                self._active_llm_span.attributes['gen_ai.usage.cost'] = cost_usd
            
            finish_reason = data.get('finish_reason')
            if finish_reason:
                self._active_llm_span.attributes['gen_ai.response.finish_reason'] = str(finish_reason)
            
            response_content = data.get('response_content')
            if response_content:
                content_str = str(response_content)
                if len(content_str) > 10000:
                    content_str = content_str[:10000] + "..."
                self._active_llm_span.attributes['gen_ai.completion.0.content'] = content_str
                self._active_llm_span.attributes['gen_ai.completion.0.role'] = 'assistant'
            
            self._manager.end_span(self._active_llm_span)
            self._active_llm_span = None
    
    def _handle_tool_start(self, event: Any) -> None:
        """Create a tool span."""
        from praisonai_tools.observability.base import SpanKind
        
        data = getattr(event, 'data', {}) or {}
        tool_name = data.get('tool_name', 'unknown')
        arguments = data.get('arguments', {})
        
        attrs = {
            'tool.name': str(tool_name),
        }
        if arguments:
            attrs['tool.arguments'] = str(arguments)
        
        span = self._manager.start_span(
            str(tool_name),
            kind=SpanKind.TOOL,
            attributes=attrs,
        )
        if span:
            span.tool_name = str(tool_name)
            span.tool_input = arguments
        self._active_tool_span = span
    
    def _handle_tool_end(self, event: Any) -> None:
        """End the tool span with result."""
        data = getattr(event, 'data', {}) or {}
        
        if self._active_tool_span:
            result = data.get('result')
            error = data.get('error')
            
            if result is not None:
                result_str = str(result)
                if len(result_str) > 10000:
                    result_str = result_str[:10000] + "..."
                self._active_tool_span.tool_output = result_str
            
            if error:
                from praisonai_tools.observability.base import SpanStatus
                self._active_tool_span.error_message = str(error)
                self._manager.end_span(self._active_tool_span, SpanStatus.ERROR)
            else:
                self._manager.end_span(self._active_tool_span)
            
            self._active_tool_span = None
