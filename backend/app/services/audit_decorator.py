from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from inspect import isawaitable, iscoroutinefunction
from typing import Any, TypeVar
from uuid import UUID

from app.services.audit_log_service import AuditLogService


T = TypeVar("T")


def audit(action: str, entity: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for service methods.

    Expects decorated service instance to provide:
    - `actor_user_id: UUID | None`
    - `audit_service: AuditLogService`
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(self, *args: Any, **kwargs: Any) -> T:
                result: T = await func(self, *args, **kwargs)  # type: ignore[misc]
                await _emit_audit_async(self=self, action=action, entity=entity, result=result, kwargs=kwargs)
                return result

            return async_wrapper

        @wraps(func)
        def sync_wrapper(self, *args: Any, **kwargs: Any) -> T:
            result = func(self, *args, **kwargs)
            _emit_audit_sync(self=self, action=action, entity=entity, result=result, kwargs=kwargs)
            return result

        return sync_wrapper

    return decorator


async def _emit_audit_async(self: Any, *, action: str, entity: str, result: Any, kwargs: dict[str, Any]) -> None:
    try:
        actor_user_id: UUID | None = getattr(self, "actor_user_id", None)
        audit_service: AuditLogService | None = getattr(self, "audit_service", None)
        if actor_user_id is None or audit_service is None:
            return

        entity_id = _resolve_entity_id(result=result, kwargs=kwargs)
        metadata = _build_metadata(kwargs=kwargs)
        log_call = audit_service.log_action(
            user_id=actor_user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            metadata=metadata,
        )
        if isawaitable(log_call):
            await log_call
    except Exception:
        # Best-effort by design.
        return None


def _emit_audit_sync(self: Any, *, action: str, entity: str, result: Any, kwargs: dict[str, Any]) -> None:
    try:
        actor_user_id: UUID | None = getattr(self, "actor_user_id", None)
        audit_service: AuditLogService | None = getattr(self, "audit_service", None)
        if actor_user_id is None or audit_service is None:
            return

        entity_id = _resolve_entity_id(result=result, kwargs=kwargs)
        metadata = _build_metadata(kwargs=kwargs)
        log_call = audit_service.log_action(
            user_id=actor_user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            metadata=metadata,
        )
        if isawaitable(log_call):
            # Do not block sync flow; audit is best-effort.
            return None
    except Exception:
        return None


def _resolve_entity_id(*, result: Any, kwargs: dict[str, Any]) -> UUID | None:
    if hasattr(result, "id"):
        value = getattr(result, "id")
        if isinstance(value, UUID):
            return value
    for key in ("client_id", "entity_id", "id"):
        value = kwargs.get(key)
        if isinstance(value, UUID):
            return value
    return None


def _build_metadata(*, kwargs: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {"name", "phone", "email", "source", "comment", "expected_version"}
    metadata: dict[str, Any] = {}
    for key in allowed_keys:
        if key in kwargs and kwargs[key] is not None:
            metadata[key] = kwargs[key]
    return metadata
