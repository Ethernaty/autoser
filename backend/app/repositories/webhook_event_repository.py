from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.webhook_event import WebhookEvent
from app.repositories.base import BaseRepositoryTenantScoped


class WebhookEventRepository(BaseRepositoryTenantScoped[WebhookEvent]):
    """Tenant-scoped webhook event store repository."""

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=WebhookEvent, tenant_id=tenant_id)

    def create_event(self, *, event_name: str, payload: dict[str, Any]) -> WebhookEvent:
        return self.create(event_name=event_name, payload=payload)
