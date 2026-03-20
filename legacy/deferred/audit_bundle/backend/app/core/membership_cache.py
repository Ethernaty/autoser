from __future__ import annotations

from uuid import UUID

from app.core.cache import get_cache_backend, get_sync_cache_adapter


def membership_cache_key(*, tenant_id: UUID, user_id: UUID) -> str:
    return f"auth:membership:{tenant_id}:{user_id}"


def invalidate_membership_cache_sync(*, tenant_id: UUID, user_id: UUID) -> None:
    cache = get_sync_cache_adapter()
    try:
        cache.delete(membership_cache_key(tenant_id=tenant_id, user_id=user_id))
    except Exception:
        return


async def invalidate_membership_cache_async(*, tenant_id: UUID, user_id: UUID) -> None:
    cache = get_cache_backend()
    try:
        await cache.delete(membership_cache_key(tenant_id=tenant_id, user_id=user_id))
    except Exception:
        return
