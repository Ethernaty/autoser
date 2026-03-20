from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.tracing import extract_context, get_current_trace_state, mark_span_error, start_span


class TracingMiddleware(BaseHTTPMiddleware):
    """OpenTelemetry-compatible request tracing middleware."""

    async def dispatch(self, request: Request, call_next):
        carrier = {key: value for key, value in request.headers.items()}
        parent_context = extract_context(carrier)

        with start_span(
            "http.request",
            attributes={
                "http.method": request.method,
                "http.route": request.url.path,
                "http.target": str(request.url),
            },
            context=parent_context,
        ) as span:
            trace_state = get_current_trace_state()
            if trace_state.trace_id is not None:
                request.state.trace_id = trace_state.trace_id

            response: Response | None = None
            status_code = 500
            try:
                response = await call_next(request)
                status_code = response.status_code
                return response
            except Exception as exc:
                mark_span_error(span, exc)
                raise
            finally:
                span.set_attribute("http.status_code", status_code)
                if response is not None and trace_state.trace_id is not None:
                    response.headers["X-Trace-ID"] = trace_state.trace_id
