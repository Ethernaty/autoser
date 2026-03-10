from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.cache import get_cache_backend
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.prometheus_metrics import get_metrics_registry
from app.core.request_context import ExternalAuthContext, get_external_auth_context
from app.services.audit_log_service import AuditLogService


class ExternalPlatformMiddleware(BaseHTTPMiddleware):
    """Enforce external API access, per-principal limits, metrics and audit logging."""

    EXTERNAL_PREFIX = "/external/"

    def __init__(self, app):
        super().__init__(app)
        settings = get_settings()
        self._cache = get_cache_backend()
        self._limit = settings.external_api_rate_limit_per_key
        self._window_seconds = settings.external_api_rate_limit_window_seconds
        self._metrics = get_metrics_registry()

    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith(self.EXTERNAL_PREFIX):
            return await call_next(request)

        try:
            auth_context = get_external_auth_context(request)
        except AppError as exc:
            return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

        limit_error = await self._enforce_rate_limit(request=request, auth_context=auth_context)
        if limit_error is not None:
            return limit_error

        started = time.perf_counter()
        response = await call_next(request)
        duration = max(0.0, time.perf_counter() - started)

        self._metrics.observe_histogram(
            "external_requests_latency_seconds",
            duration,
            labels={
                "auth_type": auth_context.auth_type,
                "method": request.method.upper(),
                "route": self._resolve_route_key(request),
            },
        )
        await self._audit_request(request=request, auth_context=auth_context, status_code=response.status_code)
        return response

    async def _enforce_rate_limit(self, *, request: Request, auth_context: ExternalAuthContext) -> Response | None:
        route = self._resolve_route_key(request)
        key = (
            f"tenant:{auth_context.tenant_id}:external:rl:"
            f"{auth_context.auth_type}:{auth_context.principal_id}:"
            f"{request.method.upper()}:{route}"
        )
        try:
            current = await self._cache.increment(key, 1, self._window_seconds)
        except Exception:
            return None

        if int(current) <= self._limit:
            return None

        error = AppError(
            status_code=429,
            code="external_rate_limit_exceeded",
            message="External API rate limit exceeded",
            details={"limit": self._limit, "window_seconds": self._window_seconds},
        )
        self._metrics.increment_counter(
            "rate_limit_rejections_total",
            labels={"route": route, "identifier_type": auth_context.auth_type},
        )
        return JSONResponse(status_code=error.status_code, content=error.to_dict())

    async def _audit_request(
        self,
        *,
        request: Request,
        auth_context: ExternalAuthContext,
        status_code: int,
    ) -> None:
        try:
            service = AuditLogService(tenant_id=auth_context.tenant_id)
            await service.log_action(
                user_id=auth_context.principal_id,
                action="external_api_request",
                entity="external_api",
                entity_id=None,
                metadata={
                    "path": request.url.path,
                    "method": request.method.upper(),
                    "status_code": status_code,
                    "auth_type": auth_context.auth_type,
                    "api_key_id": str(auth_context.api_key_id) if auth_context.api_key_id else None,
                },
            )
        except Exception:
            return

    @staticmethod
    def _resolve_route_key(request: Request) -> str:
        route = request.scope.get("route")
        if route is not None and hasattr(route, "path"):
            return str(route.path)
        return request.url.path
