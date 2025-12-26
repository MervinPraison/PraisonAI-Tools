"""
Base Provider Interface

Abstract base class for all observability providers.
"""

import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional, Union

from praisonai_tools.observability.config import ObservabilityConfig


class SpanKind(Enum):
    """Types of spans in the observability system."""
    AGENT = "agent"
    LLM = "llm"
    TOOL = "tool"
    RETRIEVAL = "retrieval"
    CHAIN = "chain"
    WORKFLOW = "workflow"
    CUSTOM = "custom"


class SpanStatus(Enum):
    """Status of a span."""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanContext:
    """Context for span propagation."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    
    @classmethod
    def new(cls, parent: Optional["SpanContext"] = None) -> "SpanContext":
        """Create a new span context."""
        return cls(
            trace_id=parent.trace_id if parent else str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=parent.span_id if parent else None,
        )


@dataclass
class Span:
    """Represents a single span in a trace."""
    name: str
    kind: SpanKind
    context: SpanContext
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    # LLM-specific
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    
    # Tool-specific
    tool_name: Optional[str] = None
    tool_input: Optional[Any] = None
    tool_output: Optional[Any] = None
    
    # Error info
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    def end(self, status: SpanStatus = SpanStatus.OK) -> None:
        """End the span."""
        self.end_time = datetime.now(timezone.utc)
        self.status = status
    
    def set_error(self, error: Exception) -> None:
        """Set error information."""
        self.status = SpanStatus.ERROR
        self.error_message = str(error)
        self.error_type = type(error).__name__
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the span."""
        self.events.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {},
        })
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Get span duration in milliseconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "name": self.name,
            "kind": self.kind.value,
            "trace_id": self.context.trace_id,
            "span_id": self.context.span_id,
            "parent_span_id": self.context.parent_span_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value,
            "attributes": self.attributes,
            "events": self.events,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "duration_ms": self.duration_ms,
        }


@dataclass
class Trace:
    """Represents a complete trace."""
    trace_id: str
    name: str
    spans: List[Span] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    
    def add_span(self, span: Span) -> None:
        """Add a span to the trace."""
        self.spans.append(span)
    
    def end(self) -> None:
        """End the trace."""
        self.end_time = datetime.now(timezone.utc)
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Get trace duration in milliseconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary."""
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "spans": [s.to_dict() for s in self.spans],
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "metadata": self.metadata,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "duration_ms": self.duration_ms,
        }


class BaseObservabilityProvider(ABC):
    """Abstract base class for observability providers."""
    
    name: str = "base"
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """Initialize the provider."""
        self.config = config or ObservabilityConfig()
        self._initialized = False
        self._current_trace: Optional[Trace] = None
        self._span_stack: List[Span] = []
    
    @abstractmethod
    def init(self, **kwargs) -> bool:
        """Initialize the provider. Returns True if successful."""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the provider and flush any pending data."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider SDK is available."""
        pass
    
    @abstractmethod
    def check_connection(self) -> tuple[bool, str]:
        """Check connection to the provider. Returns (success, message)."""
        pass
    
    @abstractmethod
    def export_span(self, span: Span) -> bool:
        """Export a span to the provider."""
        pass
    
    @abstractmethod
    def export_trace(self, trace: Trace) -> bool:
        """Export a complete trace to the provider."""
        pass
    
    def start_trace(
        self,
        name: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Trace:
        """Start a new trace."""
        trace = Trace(
            trace_id=str(uuid.uuid4()),
            name=name,
            session_id=session_id or self.config.session_id,
            user_id=user_id or self.config.user_id,
            metadata=metadata or {},
        )
        trace.agent_id = agent_id
        self._current_trace = trace
        return trace
    
    def end_trace(self, trace: Optional[Trace] = None) -> None:
        """End a trace and export it."""
        trace = trace or self._current_trace
        if trace:
            trace.end()
            self.export_trace(trace)
            if trace == self._current_trace:
                self._current_trace = None
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.CUSTOM,
        parent: Optional[Span] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Start a new span."""
        parent_context = None
        if parent:
            parent_context = parent.context
        elif self._span_stack:
            parent_context = self._span_stack[-1].context
        elif self._current_trace:
            parent_context = SpanContext(
                trace_id=self._current_trace.trace_id,
                span_id="root",
            )
        
        span = Span(
            name=name,
            kind=kind,
            context=SpanContext.new(parent_context),
            attributes=attributes or {},
        )
        self._span_stack.append(span)
        
        if self._current_trace:
            self._current_trace.add_span(span)
        
        return span
    
    def end_span(
        self,
        span: Optional[Span] = None,
        status: SpanStatus = SpanStatus.OK,
    ) -> None:
        """End a span and export it."""
        span = span or (self._span_stack[-1] if self._span_stack else None)
        if span:
            span.end(status)
            self.export_span(span)
            if span in self._span_stack:
                self._span_stack.remove(span)
    
    @contextmanager
    def trace(
        self,
        name: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Generator[Trace, None, None]:
        """Context manager for traces."""
        trace = self.start_trace(name, session_id, user_id, agent_id, metadata)
        try:
            yield trace
        except Exception as e:
            trace.metadata["error"] = str(e)
            raise
        finally:
            self.end_trace(trace)
    
    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.CUSTOM,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Generator[Span, None, None]:
        """Context manager for spans."""
        span = self.start_span(name, kind, attributes=attributes)
        try:
            yield span
        except Exception as e:
            span.set_error(e)
            raise
        finally:
            self.end_span(span)
    
    def log_llm_call(
        self,
        model: str,
        input_messages: Any,
        output: Any,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        duration_ms: Optional[float] = None,
        error: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Log an LLM call."""
        span = self.start_span(f"llm.{model}", SpanKind.LLM)
        span.model = model
        span.input_tokens = input_tokens
        span.output_tokens = output_tokens
        span.total_tokens = (input_tokens or 0) + (output_tokens or 0) if input_tokens or output_tokens else None
        span.attributes["input"] = str(input_messages) if not self.config.redact_inputs else "[REDACTED]"
        span.attributes["output"] = str(output) if not self.config.redact_outputs else "[REDACTED]"
        span.attributes.update(metadata or {})
        
        if error:
            span.set_error(error)
        
        self.end_span(span, SpanStatus.ERROR if error else SpanStatus.OK)
        return span
    
    def log_tool_call(
        self,
        tool_name: str,
        tool_input: Any,
        tool_output: Any,
        duration_ms: Optional[float] = None,
        error: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Log a tool call."""
        span = self.start_span(f"tool.{tool_name}", SpanKind.TOOL)
        span.tool_name = tool_name
        span.tool_input = tool_input if not self.config.redact_inputs else "[REDACTED]"
        span.tool_output = tool_output if not self.config.redact_outputs else "[REDACTED]"
        span.attributes.update(metadata or {})
        
        if error:
            span.set_error(error)
        
        self.end_span(span, SpanStatus.ERROR if error else SpanStatus.OK)
        return span
    
    def log_agent_step(
        self,
        agent_name: str,
        step_name: str,
        input_data: Any,
        output_data: Any,
        error: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Log an agent step."""
        span = self.start_span(f"agent.{agent_name}.{step_name}", SpanKind.AGENT)
        span.attributes["agent_name"] = agent_name
        span.attributes["step_name"] = step_name
        span.attributes["input"] = str(input_data) if not self.config.redact_inputs else "[REDACTED]"
        span.attributes["output"] = str(output_data) if not self.config.redact_outputs else "[REDACTED]"
        span.attributes.update(metadata or {})
        
        if error:
            span.set_error(error)
        
        self.end_span(span, SpanStatus.ERROR if error else SpanStatus.OK)
        return span
    
    def decorator(self, name: Optional[str] = None, kind: SpanKind = SpanKind.CUSTOM):
        """Decorator to trace a function."""
        def wrapper(func: Callable) -> Callable:
            span_name = name or func.__name__
            
            def wrapped(*args, **kwargs):
                with self.span(span_name, kind):
                    return func(*args, **kwargs)
            
            async def async_wrapped(*args, **kwargs):
                with self.span(span_name, kind):
                    return await func(*args, **kwargs)
            
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapped
            return wrapped
        
        return wrapper
