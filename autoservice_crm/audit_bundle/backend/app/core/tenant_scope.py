from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from uuid import UUID


_current_tenant_id: ContextVar[UUID | None] = ContextVar("current_tenant_id", default=None)
_current_user_id: ContextVar[UUID | None] = ContextVar("current_user_id", default=None)
_current_role: ContextVar[str | None] = ContextVar("current_role", default=None)
_current_request_id: ContextVar[str | None] = ContextVar("current_request_id", default=None)
_current_correlation_id: ContextVar[str | None] = ContextVar("current_correlation_id", default=None)
_current_endpoint: ContextVar[str | None] = ContextVar("current_endpoint", default=None)


@dataclass(frozen=True)
class TenantScopeSnapshot:
    tenant_id: UUID | None
    user_id: UUID | None
    role: str | None
    request_id: str | None
    correlation_id: str | None
    endpoint: str | None


def snapshot_scope() -> TenantScopeSnapshot:
    return TenantScopeSnapshot(
        tenant_id=_current_tenant_id.get(),
        user_id=_current_user_id.get(),
        role=_current_role.get(),
        request_id=_current_request_id.get(),
        correlation_id=_current_correlation_id.get(),
        endpoint=_current_endpoint.get(),
    )


def get_current_tenant_id(*, required: bool = False) -> UUID | None:
    tenant_id = _current_tenant_id.get()
    if required and tenant_id is None:
        from app.core.exceptions import TenantScopeError

        raise TenantScopeError(code="tenant_scope_required", message="Tenant scope is required")
    return tenant_id


def get_current_user_id() -> UUID | None:
    return _current_user_id.get()


def get_current_role() -> str | None:
    return _current_role.get()


def get_current_endpoint() -> str | None:
    return _current_endpoint.get()


def get_current_request_id() -> str | None:
    return _current_request_id.get()


def set_request_scope(*, request_id: str, correlation_id: str, endpoint: str) -> tuple[Token, Token, Token]:
    return (
        _current_request_id.set(request_id),
        _current_correlation_id.set(correlation_id),
        _current_endpoint.set(endpoint),
    )


def reset_request_scope(tokens: tuple[Token, Token, Token]) -> None:
    _current_request_id.reset(tokens[0])
    _current_correlation_id.reset(tokens[1])
    _current_endpoint.reset(tokens[2])


def set_tenant_scope(*, tenant_id: UUID, user_id: UUID | None, role: str | None) -> tuple[Token, Token, Token]:
    return (
        _current_tenant_id.set(tenant_id),
        _current_user_id.set(user_id),
        _current_role.set(role),
    )


def reset_tenant_scope(tokens: tuple[Token, Token, Token]) -> None:
    _current_tenant_id.reset(tokens[0])
    _current_user_id.reset(tokens[1])
    _current_role.reset(tokens[2])


@contextmanager
def tenant_scope_context(*, tenant_id: UUID, user_id: UUID | None, role: str | None):
    tokens = set_tenant_scope(tenant_id=tenant_id, user_id=user_id, role=role)
    try:
        yield
    finally:
        reset_tenant_scope(tokens)
