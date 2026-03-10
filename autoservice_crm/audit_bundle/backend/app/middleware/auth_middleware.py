from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.exceptions import AppError, AuthError
from app.services.jwt_service import TokenPayload, TokenType, extract_bearer_token, get_jwt_service


class AuthMiddleware(BaseHTTPMiddleware):
    """Validate access token and revocation status."""

    PUBLIC_PATHS = {
        "/health",
        "/health/live",
        "/health/ready",
        "/health/deps",
        "/metrics",
        "/docs",
        "/docs/oauth2-redirect",
        "/openapi.json",
        "/redoc",
        "/auth/register",
        "/auth/login",
        "/auth/refresh",
        "/auth/logout",
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        if getattr(request.state, "api_key_context", None) is not None:
            return await call_next(request)

        if self._is_public_path(request.url.path):
            return await call_next(request)

        jwt_service = get_jwt_service()
        try:
            token = extract_bearer_token(request.headers.get("Authorization"))
            payload = await jwt_service.decode_async(
                token,
                expected_type=TokenType.ACCESS,
                check_revoked=True,
                fail_closed=True,
            )
        except AppError as exc:
            return JSONResponse(status_code=exc.status_code, content=exc.to_dict())
        except Exception:
            fallback = AuthError(code="invalid_token", message="Invalid or expired access token")
            return JSONResponse(status_code=fallback.status_code, content=fallback.to_dict())

        request.state.token_payload = payload
        return await call_next(request)

    @classmethod
    def _is_public_path(cls, path: str) -> bool:
        if path in cls.PUBLIC_PATHS:
            return True
        return path == "/internal" or path.startswith("/internal/")


def get_request_token_payload(request: Request) -> TokenPayload:
    payload = getattr(request.state, "token_payload", None)
    if payload is None:
        raise AuthError(code="missing_token_payload", message="Token payload missing")
    return payload
