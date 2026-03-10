from __future__ import annotations

import secrets
from urllib.parse import urlencode

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, Response

from app.core.config import get_settings


ADMIN_PREFIX = "/admin"
APP_PREFIX = "/app"
ADMIN_LOGIN_PATH = "/admin/auth/login"
ADMIN_LOGOUT_PATH = "/admin/auth/logout"
ADMIN_DASHBOARD_PATH = "/admin/dashboard"
APP_HOME_PATH = "/app/clients"

ACCESS_COOKIE_NAME = "admin_access_token"
REFRESH_COOKIE_NAME = "admin_refresh_token"
SESSION_COOKIE_NAME = "admin_session_id"
CSRF_COOKIE_NAME = "admin_csrf_token"
CSRF_FORM_FIELD = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"


def normalize_next_path(next_path: str | None) -> str:
    if not next_path:
        return ADMIN_DASHBOARD_PATH
    if next_path.startswith(ADMIN_PREFIX) or next_path.startswith(APP_PREFIX):
        return next_path
    return ADMIN_DASHBOARD_PATH


def is_secure_request(request: Request) -> bool:
    settings = get_settings()
    return request.url.scheme == "https" or settings.app_env in {"production", "staging"}


def generate_session_id() -> str:
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/")
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")


class PresentationAuthMiddleware(BaseHTTPMiddleware):
    PUBLIC_PATHS = {ADMIN_LOGIN_PATH, ADMIN_LOGOUT_PATH}

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if not self._is_protected_path(path):
            return await call_next(request)

        if path in self.PUBLIC_PATHS:
            return await call_next(request)

        access_token = request.cookies.get(ACCESS_COOKIE_NAME)
        if not access_token:
            return self._redirect_to_login(request)

        self._inject_authorization_header(request, access_token)
        response = await call_next(request)

        if response.status_code == 401:
            redirect = self._redirect_to_login(request)
            clear_auth_cookies(redirect)
            return redirect

        return response

    @staticmethod
    def _is_protected_path(path: str) -> bool:
        return path.startswith(ADMIN_PREFIX) or path.startswith(APP_PREFIX)

    @staticmethod
    def _inject_authorization_header(request: Request, token: str) -> None:
        headers = list(request.scope.get("headers", []))
        has_authorization = any(header_name.lower() == b"authorization" for header_name, _ in headers)
        if has_authorization:
            return

        headers.append((b"authorization", f"Bearer {token}".encode("utf-8")))
        request.scope["headers"] = headers

    @staticmethod
    def _redirect_to_login(request: Request) -> RedirectResponse:
        next_path = request.url.path
        if request.url.query:
            next_path = f"{next_path}?{request.url.query}"
        query = urlencode({"next": next_path})
        return RedirectResponse(url=f"{ADMIN_LOGIN_PATH}?{query}", status_code=303)
