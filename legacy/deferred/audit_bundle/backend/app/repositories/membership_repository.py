from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.membership_cache import invalidate_membership_cache_sync
from app.models.membership import Membership, MembershipRole


class MembershipRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, *, user_id: UUID, tenant_id: UUID, role: MembershipRole) -> Membership:
        membership = Membership(user_id=user_id, tenant_id=tenant_id, role=role)
        self.db.add(membership)
        self.db.flush()
        return membership

    def get_for_user_and_tenant(self, *, user_id: UUID, tenant_id: UUID) -> Membership | None:
        stmt = select(Membership).where(
            Membership.user_id == user_id,
            Membership.tenant_id == tenant_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_user(self, user_id: UUID) -> list[Membership]:
        stmt = select(Membership).where(Membership.user_id == user_id)
        return list(self.db.execute(stmt).scalars().all())

    def update_role(self, *, user_id: UUID, tenant_id: UUID, role: MembershipRole) -> Membership | None:
        membership = self.get_for_user_and_tenant(user_id=user_id, tenant_id=tenant_id)
        if membership is None:
            return None
        membership.role = role
        self.db.flush()
        invalidate_membership_cache_sync(tenant_id=tenant_id, user_id=user_id)
        return membership
