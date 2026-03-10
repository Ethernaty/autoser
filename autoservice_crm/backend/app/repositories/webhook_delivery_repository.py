from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.webhook_delivery import WebhookDelivery
from app.repositories.base import BaseRepositoryTenantScoped


class WebhookDeliveryRepository(BaseRepositoryTenantScoped[WebhookDelivery]):
    """Tenant-scoped webhook delivery repository."""

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=WebhookDelivery, tenant_id=tenant_id)

    def create_delivery(
        self,
        *,
        endpoint_id: UUID,
        event_id: UUID,
        max_attempts: int,
    ) -> WebhookDelivery:
        return self.create(
            endpoint_id=endpoint_id,
            event_id=event_id,
            status="pending",
            attempt=0,
            max_attempts=max_attempts,
        )

    def mark_success(
        self,
        *,
        delivery_id: UUID,
        response_code: int | None,
        response_body: str | None,
        delivered_at: datetime,
    ) -> WebhookDelivery | None:
        entity = self.get_by_id(delivery_id)
        if entity is None:
            return None
        entity.status = "success"
        entity.response_code = response_code
        entity.response_body = response_body
        entity.error = None
        entity.next_retry_at = None
        entity.delivered_at = delivered_at
        self.db.flush()
        return entity

    def mark_failed(
        self,
        *,
        delivery_id: UUID,
        attempt: int,
        error: str,
        next_retry_at: datetime | None,
        status: str,
        response_code: int | None = None,
        response_body: str | None = None,
    ) -> WebhookDelivery | None:
        entity = self.get_by_id(delivery_id)
        if entity is None:
            return None
        entity.status = status
        entity.attempt = attempt
        entity.error = error
        entity.response_code = response_code
        entity.response_body = response_body
        entity.next_retry_at = next_retry_at
        self.db.flush()
        return entity

    def get_with_ids(self, *, delivery_id: UUID) -> WebhookDelivery | None:
        stmt = self.scoped_select(WebhookDelivery.id == delivery_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_paginated(self, *, limit: int, offset: int, status: str | None = None) -> list[WebhookDelivery]:
        criteria = []
        if status:
            criteria.append(WebhookDelivery.status == status)
        stmt = self.scoped_select(*criteria).order_by(WebhookDelivery.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())
