from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.idempotency_key import IdempotencyKey, IdempotencyStatus
from app.repositories.base import BaseRepositoryTenantScoped


class IdempotencyRepository(BaseRepositoryTenantScoped[IdempotencyKey]):
    """Tenant-scoped idempotency key storage."""

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=IdempotencyKey, tenant_id=tenant_id)

    def get_for_scope(self, *, actor_id: UUID, route: str, key: str) -> IdempotencyKey | None:
        stmt = self.scoped_select(
            IdempotencyKey.actor_id == actor_id,
            IdempotencyKey.route == route,
            IdempotencyKey.key == key,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def reserve(
        self,
        *,
        actor_id: UUID,
        route: str,
        key: str,
        request_hash: str,
        expires_at: datetime,
    ) -> IdempotencyKey:
        return self.create(
            actor_id=actor_id,
            route=route,
            key=key,
            request_hash=request_hash,
            status=IdempotencyStatus.PROCESSING.value,
            response_payload=None,
            expires_at=expires_at,
        )

    def mark_succeeded(self, *, record_id: UUID, response_payload: dict) -> None:
        record = self.get_by_id(record_id)
        if record is None:
            return
        record.status = IdempotencyStatus.SUCCEEDED.value
        record.response_payload = response_payload
        self.db.flush()

    def mark_failed(self, *, record_id: UUID) -> None:
        record = self.get_by_id(record_id)
        if record is None:
            return
        record.status = IdempotencyStatus.FAILED.value
        self.db.flush()

    def cleanup_expired(self) -> int:
        stmt = delete(IdempotencyKey).where(
            IdempotencyKey.tenant_id == self.tenant_id,
            IdempotencyKey.expires_at < datetime.now(UTC),
        )
        result = self.db.execute(stmt)
        return int(result.rowcount or 0)
