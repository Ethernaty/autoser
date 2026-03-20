from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.workspace_settings import WorkspaceSettings
from app.repositories.base import BaseRepositoryTenantScoped


class WorkspaceSettingsRepository(BaseRepositoryTenantScoped[WorkspaceSettings]):
    """Tenant-scoped data access for workspace settings."""

    ALLOWED_UPDATE_FIELDS = {"service_name", "phone", "address", "timezone", "currency", "working_hours_note"}

    def __init__(self, db: Session, tenant_id=None):
        super().__init__(db=db, model=WorkspaceSettings, tenant_id=tenant_id)

    def get_current(self) -> WorkspaceSettings | None:
        stmt = self.scoped_select()
        return self.db.execute(stmt).scalar_one_or_none()

    def update(self, entity: WorkspaceSettings, **updates: object) -> WorkspaceSettings:
        for field, value in updates.items():
            if field not in self.ALLOWED_UPDATE_FIELDS:
                continue
            setattr(entity, field, value)
        self.db.flush()
        return entity
