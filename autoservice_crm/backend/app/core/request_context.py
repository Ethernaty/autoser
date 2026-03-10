from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Request

from app.core.exceptions import AppError


@dataclass(frozen=True)
class UserRequestContext:
    user_id: UUID
    tenant_id: UUID
    role: str
    membership_version: int
    api_key_id: UUID | None = None
    auth_type: str = "jwt"


@dataclass(frozen=True)
class ApiKeyRequestContext:
    api_key_id: UUID
    tenant_id: UUID
    scopes: list[str]
    name: str


@dataclass(frozen=True)
class ExternalAuthContext:
    auth_type: str
    tenant_id: UUID
    principal_id: UUID
    role: str | None
    scopes: list[str]
    api_key_id: UUID | None = None


def get_current_user_context(request: Request) -> UserRequestContext:
    context = getattr(request.state, "user_context", None)
    if context is None:
        raise AppError(
            status_code=401,
            code="missing_auth_context",
            message="Authentication context is missing",
        )
    return context


def get_current_tenant_id(context: UserRequestContext = Depends(get_current_user_context)) -> UUID:
    return context.tenant_id


def get_current_role(context: UserRequestContext = Depends(get_current_user_context)) -> str:
    return context.role


def get_current_api_key_context(request: Request) -> ApiKeyRequestContext:
    context = getattr(request.state, "api_key_context", None)
    if context is None:
        raise AppError(status_code=401, code="missing_api_key_context", message="API key context is missing")
    return context


def get_external_auth_context(request: Request) -> ExternalAuthContext:
    api_key_context = getattr(request.state, "api_key_context", None)
    if api_key_context is not None:
        assert isinstance(api_key_context, ApiKeyRequestContext)
        return ExternalAuthContext(
            auth_type="api_key",
            tenant_id=api_key_context.tenant_id,
            principal_id=api_key_context.api_key_id,
            role=None,
            scopes=list(api_key_context.scopes),
            api_key_id=api_key_context.api_key_id,
        )

    user_context = getattr(request.state, "user_context", None)
    if user_context is not None:
        assert isinstance(user_context, UserRequestContext)
        return ExternalAuthContext(
            auth_type=user_context.auth_type,
            tenant_id=user_context.tenant_id,
            principal_id=user_context.user_id,
            role=user_context.role,
            scopes=[],
            api_key_id=user_context.api_key_id,
        )

    raise AppError(status_code=401, code="external_auth_required", message="External authentication is required")
