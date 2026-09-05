from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.dashboard_preference import DashboardPreference
from app.repositories.base import BaseRepositoryTenantScoped


class DashboardPreferenceRepository(BaseRepositoryTenantScoped[DashboardPreference]):
    """Tenant-scoped data access for dashboard preferences."""

    ALLOWED_UPDATE_FIELDS = {"mode", "filters_json", "layout_json", "baseline_version"}

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=DashboardPreference, tenant_id=tenant_id)

    def get_for_user(self, *, user_id: UUID) -> DashboardPreference | None:
        stmt = self.scoped_select(DashboardPreference.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def update(self, current: DashboardPreference, **updates: object) -> DashboardPreference:
        for field, value in updates.items():
            if field not in self.ALLOWED_UPDATE_FIELDS:
                continue
            setattr(current, field, value)
        self.db.flush()
        self.db.refresh(current)
        return current
