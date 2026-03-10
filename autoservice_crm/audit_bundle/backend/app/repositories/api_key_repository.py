from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.api_key import ApiKey


class ApiKeyRepository:
    """Repository for API key persistence and lookup."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        tenant_id: UUID,
        name: str,
        key_prefix: str,
        hashed_key: str,
        scopes: list[str],
        expires_at: datetime | None,
    ) -> ApiKey:
        entity = ApiKey(
            tenant_id=tenant_id,
            name=name,
            key_prefix=key_prefix,
            hashed_key=hashed_key,
            scopes=scopes,
            expires_at=expires_at,
        )
        self.db.add(entity)
        self.db.flush()
        return entity

    def list_for_tenant(self, *, tenant_id: UUID, include_revoked: bool = False) -> list[ApiKey]:
        stmt = select(ApiKey).where(ApiKey.tenant_id == tenant_id)
        if not include_revoked:
            stmt = stmt.where(ApiKey.revoked_at.is_(None))
        stmt = stmt.order_by(ApiKey.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id_for_tenant(self, *, tenant_id: UUID, api_key_id: UUID) -> ApiKey | None:
        stmt = select(ApiKey).where(
            ApiKey.id == api_key_id,
            ApiKey.tenant_id == tenant_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def revoke(self, *, tenant_id: UUID, api_key_id: UUID, revoked_at: datetime) -> ApiKey | None:
        entity = self.get_by_id_for_tenant(tenant_id=tenant_id, api_key_id=api_key_id)
        if entity is None:
            return None
        entity.revoked_at = revoked_at
        self.db.flush()
        return entity

    def find_candidates_by_prefix(self, *, key_prefix: str, now: datetime) -> list[ApiKey]:
        stmt = select(ApiKey).where(
            ApiKey.key_prefix == key_prefix,
            ApiKey.revoked_at.is_(None),
            or_(ApiKey.expires_at.is_(None), ApiKey.expires_at > now),
        )
        return list(self.db.execute(stmt).scalars().all())

    def update_last_used(self, *, api_key_id: UUID, last_used_at: datetime) -> None:
        stmt = select(ApiKey).where(ApiKey.id == api_key_id)
        entity = self.db.execute(stmt).scalar_one_or_none()
        if entity is None:
            return
        entity.last_used_at = last_used_at
        self.db.flush()
