from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tenant_feature_override import TenantFeatureOverride
from app.repositories.base import BaseRepositoryTenantScoped


class TenantFeatureOverrideRepository(BaseRepositoryTenantScoped[TenantFeatureOverride]):
    """Tenant-scoped repository for feature overrides."""

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=TenantFeatureOverride, tenant_id=tenant_id)

    def get_by_feature_name(self, feature_name: str) -> TenantFeatureOverride | None:
        stmt = self.scoped_select(TenantFeatureOverride.feature_name == feature_name)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert(self, *, feature_name: str, enabled: bool) -> TenantFeatureOverride:
        existing = self.get_by_feature_name(feature_name)
        if existing is None:
            return self.create(feature_name=feature_name, enabled=enabled)
        existing.enabled = enabled
        self.db.flush()
        return existing

    def delete_by_feature_name(self, feature_name: str) -> bool:
        entity = self.get_by_feature_name(feature_name)
        if entity is None:
            return False
        self.db.delete(entity)
        self.db.flush()
        return True

    def list_all(self) -> list[TenantFeatureOverride]:
        stmt = self.scoped_select().order_by(TenantFeatureOverride.feature_name.asc())
        return list(self.db.execute(stmt).scalars().all())
