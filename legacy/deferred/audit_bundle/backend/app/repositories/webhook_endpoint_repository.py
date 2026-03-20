from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.webhook_endpoint import WebhookEndpoint
from app.repositories.base import BaseRepositoryTenantScoped


class WebhookEndpointRepository(BaseRepositoryTenantScoped[WebhookEndpoint]):
    """Tenant-scoped webhook endpoint repository."""

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=WebhookEndpoint, tenant_id=tenant_id)

    def list_active(self) -> list[WebhookEndpoint]:
        stmt = self.scoped_select(WebhookEndpoint.is_active.is_(True)).order_by(WebhookEndpoint.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def list_all(self) -> list[WebhookEndpoint]:
        stmt = self.scoped_select().order_by(WebhookEndpoint.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def deactivate(self, endpoint_id: UUID) -> bool:
        entity = self.get_by_id(endpoint_id)
        if entity is None:
            return False
        entity.is_active = False
        self.db.flush()
        return True
