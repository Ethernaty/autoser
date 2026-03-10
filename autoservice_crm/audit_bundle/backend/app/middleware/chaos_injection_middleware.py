from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.reliability.chaos import ChaosInjectedError, get_chaos_engine


class ChaosInjectionMiddleware(BaseHTTPMiddleware):
    """Request-level chaos injection middleware for resilience validation."""

    EXEMPT_PATHS = {
        "/health",
        "/health/live",
        "/health/ready",
        "/health/deps",
        "/metrics",
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        chaos = get_chaos_engine()
        try:
            chaos.maybe_raise_random_exception()
        except ChaosInjectedError:
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "code": "chaos_injected_exception",
                        "message": "Injected fault for resilience validation",
                        "details": {},
                    }
                },
            )

        return await call_next(request)
