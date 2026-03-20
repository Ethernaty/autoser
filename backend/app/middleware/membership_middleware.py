from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.cache import get_cache_backend
from app.core.membership_cache import invalidate_membership_cache_async, membership_cache_key
from app.core.config import get_settings
from app.core.exceptions import AppError, AuthError
from app.core.request_context import ApiKeyRequestContext, UserRequestContext
from app.core.serialization import JsonSerializer
from app.core.tenant_scope import reset_tenant_scope, set_tenant_scope
from app.core.uow import SqlAlchemyUnitOfWork
from app.repositories.membership_repository import MembershipRepository
from app.services.tenant_lifecycle_service import TenantLifecycleService
from app.services.jwt_service import TokenPayload


@dataclass
class MembershipSnapshot:
    role: str
    version: int


class MembershipValidationMiddleware(BaseHTTPMiddleware):
    """Validate tenant membership and role freshness on every authenticated request."""

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

    _ROLE_FIELD_FILTERS: dict[str, set[str]] = {
        "owner": {"password_hash"},
        "admin": {"password_hash"},
        "employee": {"password_hash", "email", "phone"},
    }

    def __init__(self, app):
        super().__init__(app)
        self._cache = get_cache_backend()
        self._serializer = JsonSerializer()
        self._ttl_seconds = max(5, get_settings().membership_cache_ttl_seconds)
        self._logger = logging.getLogger("app.security.response_filter")
        self._tenant_lifecycle = TenantLifecycleService()

    async def dispatch(self, request: Request, call_next) -> Response:
        if self._is_public_path(request.url.path):
            return await call_next(request)

        api_key_context = getattr(request.state, "api_key_context", None)
        if api_key_context is not None:
            assert isinstance(api_key_context, ApiKeyRequestContext)
            try:
                await self._tenant_lifecycle.assert_tenant_active(tenant_id=api_key_context.tenant_id)
            except AppError as exc:
                return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

            request.state.user_context = UserRequestContext(
                user_id=api_key_context.api_key_id,
                tenant_id=api_key_context.tenant_id,
                role="api_key",
                membership_version=0,
                api_key_id=api_key_context.api_key_id,
                auth_type="api_key",
            )

            tenant_tokens = set_tenant_scope(
                tenant_id=api_key_context.tenant_id,
                user_id=api_key_context.api_key_id,
                role="api_key",
            )
            try:
                return await call_next(request)
            finally:
                reset_tenant_scope(tenant_tokens)

        token_payload = getattr(request.state, "token_payload", None)
        if token_payload is None:
            error = AuthError(code="missing_token_payload", message="Token payload missing")
            return JSONResponse(status_code=error.status_code, content=error.to_dict())

        assert isinstance(token_payload, TokenPayload)
        try:
            snapshot = await self._load_cached_snapshot(
                tenant_id=token_payload.tenant_uuid,
                user_id=token_payload.user_id,
            )
            if snapshot is None:
                snapshot = await run_in_threadpool(
                    self._fetch_membership_from_db,
                    token_payload.user_id,
                    token_payload.tenant_uuid,
                )
                if snapshot is None:
                    raise AppError(status_code=403, code="tenant_mismatch", message="User has no access to tenant")

                # Cache is optimization only; DB is source of truth.
                await self._safe_cache_set(
                    membership_cache_key(tenant_id=token_payload.tenant_uuid, user_id=token_payload.user_id),
                    snapshot,
                )
        except AppError as exc:
            return JSONResponse(status_code=exc.status_code, content=exc.to_dict())
        except Exception:
            error = AuthError(code="membership_validation_failed", message="Membership validation failed")
            return JSONResponse(status_code=error.status_code, content=error.to_dict())

        if snapshot.version != token_payload.membership_version:
            error = AuthError(code="stale_token", message="Token is stale for current membership")
            return JSONResponse(status_code=error.status_code, content=error.to_dict())
        if snapshot.role != token_payload.role:
            error = AuthError(code="stale_token_role", message="Token role is stale")
            return JSONResponse(status_code=error.status_code, content=error.to_dict())
        try:
            await self._tenant_lifecycle.assert_tenant_active(tenant_id=token_payload.tenant_uuid)
        except AppError as exc:
            return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

        request.state.user_context = UserRequestContext(
            user_id=token_payload.user_id,
            tenant_id=token_payload.tenant_uuid,
            role=snapshot.role,
            membership_version=snapshot.version,
        )

        tenant_tokens = set_tenant_scope(
            tenant_id=token_payload.tenant_uuid,
            user_id=token_payload.user_id,
            role=snapshot.role,
        )
        try:
            response = await call_next(request)
        finally:
            reset_tenant_scope(tenant_tokens)

        return self._apply_response_filter(response=response, role=snapshot.role)

    @classmethod
    def _is_public_path(cls, path: str) -> bool:
        if path in cls.PUBLIC_PATHS:
            return True
        return path == "/internal" or path.startswith("/internal/")

    @staticmethod
    def _fetch_membership_from_db(user_id: UUID, tenant_id: UUID) -> MembershipSnapshot | None:
        with SqlAlchemyUnitOfWork() as uow:
            if uow.session is None:
                return None
            repo = MembershipRepository(uow.session)
            membership = repo.get_for_user_and_tenant(user_id=user_id, tenant_id=tenant_id)
            if membership is None:
                return None
            return MembershipSnapshot(role=membership.role.value, version=int(membership.version))

    async def _safe_cache_set(self, key: str, snapshot: MembershipSnapshot) -> None:
        payload: dict[str, Any] = {"role": snapshot.role, "version": snapshot.version}
        try:
            await self._cache.set(key, self._serializer.dumps(payload), self._ttl_seconds)
        except Exception:
            return

    async def _load_cached_snapshot(self, *, tenant_id: UUID, user_id: UUID) -> MembershipSnapshot | None:
        key = membership_cache_key(tenant_id=tenant_id, user_id=user_id)
        try:
            raw = await self._cache.get(key)
            if raw is None:
                return None
            payload = self._serializer.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(payload, dict):
                return None
            role = str(payload.get("role", "")).strip().lower()
            version = int(payload.get("version", 0))
            if not role:
                return None
            return MembershipSnapshot(role=role, version=version)
        except Exception:
            return None

    def _apply_response_filter(self, *, response: Response, role: str) -> Response:
        fields_to_filter = self._ROLE_FIELD_FILTERS.get(role.lower())
        if not fields_to_filter:
            return response

        if response.status_code >= 400:
            return response

        content_type = (response.headers.get("content-type") or "").lower()
        if "application/json" not in content_type:
            return response

        body = getattr(response, "body", None)
        if not isinstance(body, (bytes, bytearray)) or not body:
            return response

        try:
            payload = json.loads(body)
        except Exception:
            return response

        filtered = self._filter_payload(payload, fields_to_filter)
        try:
            encoded = json.dumps(filtered, separators=(",", ":"), default=str).encode("utf-8")
        except Exception:
            self._logger.warning("response_filter_failed")
            return response

        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(
            content=encoded,
            status_code=response.status_code,
            headers=headers,
            media_type="application/json",
        )

    def _filter_payload(self, payload: Any, fields_to_filter: set[str]) -> Any:
        if isinstance(payload, list):
            return [self._filter_payload(item, fields_to_filter) for item in payload]

        if not isinstance(payload, dict):
            return payload

        result: dict[str, Any] = {}
        for key, value in payload.items():
            key_name = str(key)
            if key_name in fields_to_filter:
                result[key_name] = self._masked_value(key_name, value)
                continue
            result[key_name] = self._filter_payload(value, fields_to_filter)
        return result

    @staticmethod
    def _masked_value(key: str, value: Any) -> Any:
        if value is None:
            return None
        if key == "phone" and isinstance(value, str) and len(value) >= 4:
            return f"{'*' * (len(value) - 4)}{value[-4:]}"
        if key == "email" and isinstance(value, str) and "@" in value:
            local, domain = value.split("@", 1)
            prefix = local[:2] if len(local) >= 2 else ""
            return f"{prefix}***@{domain}"
        if key == "password_hash":
            return "***"
        if isinstance(value, str):
            return "***"
        return None


async def invalidate_membership_cache(*, tenant_id: UUID, user_id: UUID) -> None:
    await invalidate_membership_cache_async(tenant_id=tenant_id, user_id=user_id)
