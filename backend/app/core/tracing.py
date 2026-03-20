from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings


@dataclass(frozen=True)
class TraceState:
    trace_id: str | None


class _NoopSpan:
    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return None

    def set_attribute(self, key: str, value: Any) -> None:
        return None

    def set_status(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def record_exception(self, _exc: BaseException) -> None:
        return None


class _NoopTracer:
    @contextmanager
    def start_as_current_span(self, _name: str, **_kwargs: Any):
        yield _NoopSpan()


_tracer: Any = _NoopTracer()
_propagator: Any = None
_trace_api: Any = None
_status_api: Any = None
_initialized = False


def initialize_tracing() -> None:
    global _tracer, _propagator, _trace_api, _status_api, _initialized
    if _initialized:
        return
    _initialized = True

    settings = get_settings()
    if not settings.tracing_enabled or settings.tracing_exporter == "none":
        return

    try:
        from opentelemetry import propagate, trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.trace.status import Status, StatusCode
    except Exception:
        return

    provider = TracerProvider(resource=Resource.create({"service.name": settings.tracing_service_name}))
    if settings.tracing_exporter == "console":
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
    elif settings.tracing_exporter == "otlp":
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            processor = BatchSpanProcessor(OTLPSpanExporter())
            provider.add_span_processor(processor)
        except Exception:
            processor = BatchSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(settings.tracing_service_name)
    _propagator = propagate
    _trace_api = trace
    _status_api = (Status, StatusCode)


def shutdown_tracing() -> None:
    global _initialized
    if not _initialized:
        return
    if _trace_api is None:
        return
    try:
        provider = _trace_api.get_tracer_provider()
        shutdown = getattr(provider, "shutdown", None)
        if callable(shutdown):
            shutdown()
    except Exception:
        return


@contextmanager
def start_span(name: str, *, attributes: dict[str, Any] | None = None, context: Any = None):
    kwargs: dict[str, Any] = {}
    if context is not None:
        kwargs["context"] = context
    with _tracer.start_as_current_span(name, **kwargs) as span:
        if attributes:
            for key, value in attributes.items():
                try:
                    span.set_attribute(key, value)
                except Exception:
                    continue
        yield span


def mark_span_error(span: Any, exc: BaseException) -> None:
    try:
        span.record_exception(exc)
    except Exception:
        return
    if _status_api is None:
        return
    try:
        status_cls, status_code = _status_api
        span.set_status(status_cls(status_code.ERROR))
    except Exception:
        return


def extract_context(headers: dict[str, str]) -> Any:
    if _propagator is None:
        return None
    try:
        return _propagator.extract(headers)
    except Exception:
        return None


def inject_context(headers: dict[str, str]) -> None:
    if _propagator is None:
        return
    try:
        _propagator.inject(headers)
    except Exception:
        return


def get_current_trace_state() -> TraceState:
    if _trace_api is None:
        return TraceState(trace_id=None)
    try:
        span = _trace_api.get_current_span()
        ctx = span.get_span_context()
        if ctx is None or not getattr(ctx, "is_valid", False):
            return TraceState(trace_id=None)
        return TraceState(trace_id=f"{int(ctx.trace_id):032x}")
    except Exception:
        return TraceState(trace_id=None)
