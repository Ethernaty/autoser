from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tenant import Tenant, TenantState


class TenantRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_slug(self, slug: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.slug == slug)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, *, name: str, slug: str) -> Tenant:
        tenant = Tenant(name=name, slug=slug)
        self.db.add(tenant)
        self.db.flush()
        return tenant

    def list_paginated(self, *, limit: int, offset: int) -> list[Tenant]:
        stmt = select(Tenant).order_by(Tenant.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def set_state(self, *, tenant_id: UUID, state: TenantState) -> Tenant | None:
        tenant = self.get_by_id(tenant_id)
        if tenant is None:
            return None
        tenant.state = state
        self.db.flush()
        return tenant
