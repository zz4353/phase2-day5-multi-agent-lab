"""Tracing hooks with Langfuse integration."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Any, Optional

from langfuse import Langfuse

from multi_agent_research_lab.core.config import get_settings


logger = logging.getLogger(__name__)


class LangfuseTracer:
    """Langfuse tracing client wrapper."""
    
    def __init__(self):
        """Initialize Langfuse client with settings."""
        settings = get_settings()
        
        self.enabled = bool(
            settings.langfuse_public_key and settings.langfuse_secret_key
        )
        
        if self.enabled:
            try:
                self.client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host
                )
                logger.info("Langfuse tracing initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse: {e}. Tracing will be disabled.")
                self.enabled = False
                self.client = None
        else:
            logger.warning("Langfuse keys not configured. Tracing will be disabled.")
            self.client = None
    
    def get_trace_url(self, trace_id: str) -> str:
        """Get public URL for viewing trace on Langfuse dashboard.
        
        Args:
            trace_id: Trace ID from Langfuse
            
        Returns:
            Public URL to view trace
        """
        settings = get_settings()
        base_url = settings.langfuse_host.rstrip('/')
        return f"{base_url}/trace/{trace_id}"


# Global tracer instance
_tracer: Optional[LangfuseTracer] = None


def get_tracer() -> LangfuseTracer:
    """Get or create global Langfuse tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = LangfuseTracer()
    return _tracer


@contextmanager
def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    trace_id: Optional[str] = None
) -> Iterator[dict[str, Any]]:
    """Create a trace span with Langfuse integration.
    
    Args:
        name: Name of the span
        attributes: Additional attributes to log
        trace_id: Optional trace ID to connect to existing trace
        
    Yields:
        Span dictionary with metadata
    """
    tracer = get_tracer()
    started = perf_counter()
    
    span: dict[str, Any] = {
        "name": name,
        "attributes": attributes or {},
        "duration_seconds": None,
        "trace_id": None,
        "span_id": None,
        "trace_url": None
    }
    
    langfuse_span = None
    
    try:
        if tracer.enabled and tracer.client:
            # Create Langfuse span
            if trace_id:
                # Connect to existing trace
                langfuse_span = tracer.client.start_observation(
                    name=name,
                    trace_context={"trace_id": trace_id},
                    metadata=attributes
                )
            else:
                # Create new trace
                langfuse_span = tracer.client.start_observation(
                    name=name,
                    metadata=attributes
                )
            
            # Get trace info
            if langfuse_span and hasattr(langfuse_span, '_otel_span'):
                otel_span = langfuse_span._otel_span
                span_context = otel_span.get_span_context()
                if span_context:
                    span["trace_id"] = format(span_context.trace_id, '032x')
                    span["span_id"] = format(span_context.span_id, '016x')
                    span["trace_url"] = tracer.get_trace_url(span["trace_id"])
        
        yield span
        
    finally:
        duration = perf_counter() - started
        span["duration_seconds"] = duration
        
        # End Langfuse span
        if langfuse_span:
            try:
                langfuse_span.end()
            except Exception as e:
                logger.warning(f"Failed to end Langfuse span: {e}")


@contextmanager
def trace_agent_execution(
    agent_name: str,
    input_data: Any,
    trace_id: Optional[str] = None
) -> Iterator[dict[str, Any]]:
    """Trace an agent execution with input/output logging.
    
    Args:
        agent_name: Name of the agent
        input_data: Input data for the agent
        trace_id: Optional trace ID to connect to existing trace
        
    Yields:
        Span dictionary with metadata
    """
    tracer = get_tracer()
    started = perf_counter()
    
    span: dict[str, Any] = {
        "name": f"agent_{agent_name}",
        "agent_name": agent_name,
        "input": input_data,
        "output": None,
        "duration_seconds": None,
        "trace_id": None,
        "span_id": None,
        "trace_url": None
    }
    
    langfuse_span = None
    
    try:
        if tracer.enabled and tracer.client:
            # Create Langfuse span for agent
            if trace_id:
                langfuse_span = tracer.client.start_observation(
                    name=agent_name,
                    as_type="agent",
                    trace_context={"trace_id": trace_id},
                    input=input_data
                )
            else:
                langfuse_span = tracer.client.start_observation(
                    name=agent_name,
                    as_type="agent",
                    input=input_data
                )
            
            # Get trace info
            if langfuse_span and hasattr(langfuse_span, '_otel_span'):
                otel_span = langfuse_span._otel_span
                span_context = otel_span.get_span_context()
                if span_context:
                    span["trace_id"] = format(span_context.trace_id, '032x')
                    span["span_id"] = format(span_context.span_id, '016x')
                    span["trace_url"] = tracer.get_trace_url(span["trace_id"])
        
        yield span
        
    finally:
        duration = perf_counter() - started
        span["duration_seconds"] = duration
        
        # Update and end Langfuse span
        if langfuse_span:
            try:
                if span.get("output"):
                    langfuse_span.update(output=span["output"])
                langfuse_span.end()
            except Exception as e:
                logger.warning(f"Failed to end Langfuse agent span: {e}")
