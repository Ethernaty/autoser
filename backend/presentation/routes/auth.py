from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from starlette.concurrency import run_in_threadpool

from app.controllers.auth_controller import get_auth_service
from app.core.exceptions import AppError
from app.services.auth_service import AuthService
from presentation.middleware import (
    ACCESS_COOKIE_NAME,
    ADMIN_LOGIN_PATH,
    REFRESH_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    clear_auth_cookies,
    generate_session_id,
    is_secure_request,
    normalize_next_path,
)
from presentation.services.login_security_service import get_login_rate_limiter
from presentation.templating import templates


router = APIRouter(prefix="/auth")
logger = logging.getLogger("presentation.auth")


def _set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    access_expires_in: int,
    refresh_expires_in: int,
    secure: bool,
) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=access_expires_in,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=refresh_expires_in,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=generate_session_id(),
        max_age=60 * 60 * 24,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


def _render_login(
    request: Request,
    *,
    next_path: str,
    error_message: str | None = None,
    email: str = "",
    tenant_slug: str = "",
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "next": next_path,
            "error": error_message,
            "email": email,
            "tenant_slug": tenant_slug,
        },
        status_code=status_code,
    )


@router.get("/login", response_class=HTMLResponse, name="admin_login_page")
async def login_page(request: Request, next: str | None = None) -> Response:
    if request.cookies.get(ACCESS_COOKIE_NAME):
        return RedirectResponse(url=normalize_next_path(next), status_code=status.HTTP_303_SEE_OTHER)
    return _render_login(request, next_path=normalize_next_path(next))


@router.post("/login", response_class=HTMLResponse, name="admin_login_submit")
async def login_submit(request: Request, service: AuthService = Depends(get_auth_service)) -> Response:
    form = await request.form()

    email = str(form.get("email", "")).strip()
    password = str(form.get("password", ""))
    tenant_slug = str(form.get("tenant_slug", "")).strip()
    next_path = normalize_next_path(str(form.get("next", "")))

    limiter = get_login_rate_limiter()
    rate_key = _login_rate_key(request=request, email=email)
    decision = await limiter.consume(key=rate_key)
    if not decision.allowed:
        return _render_login(
            request,
            next_path=next_path,
            error_message=f"Too many login attempts. Retry in {decision.retry_after_seconds}s.",
            email=email,
            tenant_slug=tenant_slug,
            status_code=429,
        )

    if not email or not password:
        return _render_login(
            request,
            next_path=next_path,
            error_message="Email and password are required.",
            email=email,
            tenant_slug=tenant_slug,
            status_code=400,
        )

    try:
        result = await run_in_threadpool(
            service.login,
            email=email,
            password=password,
            tenant_slug=tenant_slug or None,
        )
    except AppError as exc:
        logger.warning("presentation_login_failed", extra={"email": email, "reason": exc.code})
        return _render_login(
            request,
            next_path=next_path,
            error_message=exc.message,
            email=email,
            tenant_slug=tenant_slug,
            status_code=400,
        )
    except Exception:
        logger.exception("presentation_login_unhandled_error", extra={"email": email})
        return _render_login(
            request,
            next_path=next_path,
            error_message="Login failed. Please try again.",
            email=email,
            tenant_slug=tenant_slug,
            status_code=500,
        )

    await limiter.reset(key=rate_key)

    response = RedirectResponse(url=next_path, status_code=status.HTTP_303_SEE_OTHER)
    _set_auth_cookies(
        response,
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        access_expires_in=result.tokens.access_expires_in,
        refresh_expires_in=result.tokens.refresh_expires_in,
        secure=is_secure_request(request),
    )
    return response


@router.post("/logout", name="admin_logout")
async def logout(request: Request, service: AuthService = Depends(get_auth_service)) -> RedirectResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token:
        try:
            await run_in_threadpool(service.revoke_refresh_token, refresh_token=refresh_token)
        except Exception:
            pass

    response = RedirectResponse(url=ADMIN_LOGIN_PATH, status_code=status.HTTP_303_SEE_OTHER)
    clear_auth_cookies(response)
    return response


def _login_rate_key(*, request: Request, email: str) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    client_host = forwarded_for or (request.client.host if request.client else "unknown")
    email_fingerprint = hashlib.sha256(email.lower().encode("utf-8")).hexdigest()[:24]
    return f"{client_host}:{email_fingerprint}"
