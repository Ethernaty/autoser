from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.exceptions import AppError
from app.core.prometheus_metrics import get_metrics_registry
from app.core.request_context import ApiKeyRequestContext, UserRequestContext
from app.services.api_key_service import ApiKeyService


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Authenticate external API requests via API keys."""

    EXTERNAL_PREFIX = "/external/"

    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith(self.EXTERNAL_PREFIX):
            return await call_next(request)

        authorization = request.headers.get("Authorization")
        token = self._extract_bearer_token(authorization)
        if token is None or not token.startswith("sk_"):
            return await call_next(request)

        service = ApiKeyService(tenant_id=None)
        try:
            auth = await service.authenticate_key(raw_key=token)
        except AppError as exc:
            return JSONResponse(status_code=exc.status_code, content=exc.to_dict())
        except Exception:
            error = AppError(status_code=401, code="invalid_api_key", message="Invalid API key")
            return JSONResponse(status_code=error.status_code, content=error.to_dict())

        request.state.api_key_context = ApiKeyRequestContext(
            api_key_id=auth.api_key_id,
            tenant_id=auth.tenant_id,
            scopes=auth.scopes,
            name=auth.name,
        )
        request.state.user_context = UserRequestContext(
            user_id=auth.api_key_id,
            tenant_id=auth.tenant_id,
            role="api_key",
            membership_version=0,
            api_key_id=auth.api_key_id,
            auth_type="api_key",
        )

        get_metrics_registry().increment_counter(
            "api_key_requests_total",
            labels={"auth_type": "api_key"},
        )
        return await call_next(request)

    @staticmethod
    def _extract_bearer_token(authorization_header: str | None) -> str | None:
        if not authorization_header:
            return None
        parts = authorization_header.strip().split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        return parts[1]
