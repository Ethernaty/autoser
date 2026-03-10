from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

from app.core.observability import end_trace, get_observability_registry, start_trace


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Collect request metrics and attach trace context."""

    def __init__(self, app):
        super().__init__(app)
        self._metrics = get_observability_registry()

    async def dispatch(self, request: Request, call_next):
        trace = start_trace(request)
        request.state.trace_id = trace.trace_id
        response: Response | None = None
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_seconds = end_trace(trace)
            route_template = self._resolve_route_template(request)
            self._metrics.observe_request(
                method=request.method,
                route=route_template,
                status_code=status_code,
                duration_seconds=duration_seconds,
            )
            if response is not None:
                response.headers["X-Trace-ID"] = trace.trace_id

    @staticmethod
    def _resolve_route_template(request: Request) -> str:
        route = request.scope.get("route")
        if route is not None and hasattr(route, "path"):
            template = str(route.path)
            if template:
                return template

        for candidate in request.app.router.routes:
            try:
                match, _ = candidate.matches(request.scope)
            except Exception:
                continue
            if match == Match.FULL and hasattr(candidate, "path"):
                template = str(candidate.path)
                if template:
                    return template

        return request.url.path
