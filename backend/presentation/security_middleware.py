from __future__ import annotations

import hmac
from typing import Any
from urllib.parse import parse_qs

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.services.audit_log_service import AuditLogService
from app.services.jwt_service import TokenType, get_jwt_service
from presentation.middleware import (
    ACCESS_COOKIE_NAME,
    APP_PREFIX,
    CSRF_COOKIE_NAME,
    CSRF_FORM_FIELD,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    generate_csrf_token,
    generate_session_id,
    is_secure_request,
)
from presentation.rbac import allowed_roles_for_path, is_known_role
from presentation.templating import templates


_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class PresentationSecurityMiddleware(BaseHTTPMiddleware):
    """Presentation security layer: RBAC path guard, CSRF, audit and session rotation."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if not self._is_presentation_path(path):
            return await call_next(request)

        secure_cookie = is_secure_request(request)
        csrf_token = request.cookies.get(CSRF_COOKIE_NAME) or generate_csrf_token()
        request.state.csrf_token = csrf_token

        token_payload = await self._decode_access_payload(request)
        request.state.presentation_role = token_payload.role.strip().lower() if token_payload is not None else None

        role_gate = await self._enforce_path_roles(request=request, token_payload=token_payload)
        if role_gate is not None:
            response = role_gate
            self._set_csrf_cookie(response=response, csrf_token=csrf_token, secure=secure_cookie)
            return response

        csrf_gate = await self._enforce_csrf(request=request, token_payload=token_payload)
        if csrf_gate is not None:
            response = csrf_gate
            self._set_csrf_cookie(response=response, csrf_token=csrf_token, secure=secure_cookie)
            return response

        response = await call_next(request)

        self._set_csrf_cookie(response=response, csrf_token=csrf_token, secure=secure_cookie)
        self._rotate_session_cookie(
            request=request,
            response=response,
            secure=secure_cookie,
            token_payload=token_payload,
        )
        return response

    @staticmethod
    def _is_presentation_path(path: str) -> bool:
        if path.startswith("/admin/static"):
            return False
        return path.startswith("/admin") or path.startswith(APP_PREFIX)

    async def _decode_access_payload(self, request: Request):
        access_token = request.cookies.get(ACCESS_COOKIE_NAME)
        if not access_token:
            return None

        jwt_service = get_jwt_service()
        try:
            return await jwt_service.decode_async(
                access_token,
                expected_type=TokenType.ACCESS,
                check_revoked=True,
                fail_closed=False,
            )
        except Exception:
            return None

    async def _enforce_path_roles(self, *, request: Request, token_payload) -> Response | None:
        path = request.url.path
        allowed_roles = allowed_roles_for_path(path)
        if not allowed_roles:
            return None

        if path.startswith("/admin/auth"):
            return None

        if token_payload is None:
            return None

        role = token_payload.role.strip().lower()
        if not is_known_role(role) or role not in allowed_roles:
            await self._audit_denied(
                token_payload=token_payload,
                action="presentation.rbac.path_denied",
                request=request,
                metadata={"required_roles": sorted(allowed_roles), "role": role},
            )
            return self._forbidden_response(request=request, reason="Insufficient role for this area")

        return None

    async def _enforce_csrf(self, *, request: Request, token_payload) -> Response | None:
        if request.method.upper() in _SAFE_METHODS:
            return None

        path = request.url.path
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME) or ""
        if not cookie_token:
            await self._audit_denied(
                token_payload=token_payload,
                action="presentation.csrf.missing_cookie",
                request=request,
                metadata={"path": path},
            )
            return self._forbidden_response(request=request, reason="CSRF token missing")

        submitted_token = request.headers.get(CSRF_HEADER_NAME, "")
        if not submitted_token:
            content_type = (request.headers.get("content-type") or "").lower()
            if "application/x-www-form-urlencoded" in content_type:
                try:
                    raw_body = await request.body()
                    parsed = parse_qs(raw_body.decode("utf-8", errors="ignore"), keep_blank_values=True)
                    values = parsed.get(CSRF_FORM_FIELD, [""])
                    submitted_token = str(values[0]) if values else ""
                except Exception:
                    submitted_token = ""
            elif "multipart/form-data" in content_type:
                try:
                    form = await request.form()
                    submitted_token = str(form.get(CSRF_FORM_FIELD, ""))
                except Exception:
                    submitted_token = ""

        if not submitted_token or not hmac.compare_digest(submitted_token, cookie_token):
            await self._audit_denied(
                token_payload=token_payload,
                action="presentation.csrf.invalid",
                request=request,
                metadata={"path": path},
            )
            return self._forbidden_response(request=request, reason="CSRF validation failed")

        return None

    @staticmethod
    def _set_csrf_cookie(*, response: Response, csrf_token: str, secure: bool) -> None:
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=csrf_token,
            max_age=60 * 60 * 8,
            httponly=False,
            secure=secure,
            samesite="lax",
            path="/",
        )

    @staticmethod
    def _rotate_session_cookie(*, request: Request, response: Response, secure: bool, token_payload: Any | None) -> None:
        path = request.url.path
        if path.startswith("/admin/auth/login") or path.startswith("/admin/auth/logout"):
            return
        if not (path.startswith("/admin") or path.startswith(APP_PREFIX)):
            return
        if token_payload is None:
            return

        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=generate_session_id(),
            max_age=60 * 60 * 24,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/",
        )

    async def _audit_denied(self, *, token_payload, action: str, request: Request, metadata: dict[str, Any]) -> None:
        if token_payload is None:
            return

        try:
            audit_service = AuditLogService(tenant_id=token_payload.tenant_uuid)
            await audit_service.log_action(
                user_id=token_payload.user_id,
                action=action,
                entity="presentation_security",
                entity_id=None,
                metadata={
                    "path": request.url.path,
                    "query": dict(request.query_params),
                    **metadata,
                },
            )
        except Exception:
            return

    @staticmethod
    def _forbidden_response(*, request: Request, reason: str) -> Response:
        return templates.TemplateResponse(
            "forbidden.html",
            {
                "request": request,
                "current_user": None,
                "reason": reason,
                "next_path": request.url.path,
            },
            status_code=403,
        )
