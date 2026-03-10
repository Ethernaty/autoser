from __future__ import annotations

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach correlation id for request chain tracing across services."""

    HEADER_NAME = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(self.HEADER_NAME) or str(uuid4())
        request.state.correlation_id = correlation_id
        response: Response = await call_next(request)
        response.headers[self.HEADER_NAME] = correlation_id
        return response
