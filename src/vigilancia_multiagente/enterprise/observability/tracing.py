"""OpenTelemetry tracing setup for Vigilador.

Supports two export modes:
- Console (default): spans printed to stdout for development.
- OTLP: when VT_OTEL_EXPORTER_ENDPOINT is set, exports to a collector.
"""

from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor


def setup_tracing() -> None:
    provider = TracerProvider()

    endpoint = os.environ.get("VT_OTEL_EXPORTER_ENDPOINT")
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(SimpleSpanProcessor(exporter))
        except ImportError:
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    else:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)


def get_tracer(name: str = "vigilador") -> trace.Tracer:
    return trace.get_tracer(name)
