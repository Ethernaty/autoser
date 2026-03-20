from __future__ import annotations

import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Emit one structured log event per request."""

    def __init__(self, app):
        super().__init__(app)
        self._logger = logging.getLogger("app.http")

    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", None) or str(uuid4())
        correlation_id = getattr(request.state, "correlation_id", None) or request_id

        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        started_at = time.perf_counter()
        status_code = 500
        response: Response | None = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            latency_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
            context = getattr(request.state, "user_context", None)
            self._logger.info(
                "http_request",
                extra={
                    "request_id": request_id,
                    "correlation_id": getattr(request.state, "correlation_id", None),
                    "trace_id": getattr(request.state, "trace_id", None),
                    "tenant_id": str(context.tenant_id) if context else None,
                    "user_id": str(context.user_id) if context else None,
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                },
            )
            if response is not None and request_id:
                response.headers["X-Request-ID"] = request_id
                response.headers.setdefault("X-Correlation-ID", correlation_id)
