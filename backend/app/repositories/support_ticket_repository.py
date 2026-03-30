from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.support_ticket import SupportTicket, SupportTicketCategory, SupportTicketStatus
from app.repositories.base import BaseRepositoryTenantScoped


class SupportTicketRepository(BaseRepositoryTenantScoped[SupportTicket]):
    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=SupportTicket, tenant_id=tenant_id)

    def list_tickets(
        self,
        *,
        limit: int,
        offset: int,
        q: str | None = None,
        status: SupportTicketStatus | None = None,
        category: SupportTicketCategory | None = None,
        reporter_user_id: UUID | None = None,
    ) -> list[SupportTicket]:
        criteria: list[object] = []
        if q:
            pattern = f"%{q}%"
            criteria.append(or_(SupportTicket.subject.ilike(pattern), SupportTicket.message.ilike(pattern)))
        if status is not None:
            criteria.append(SupportTicket.status == status)
        if category is not None:
            criteria.append(SupportTicket.category == category)
        if reporter_user_id is not None:
            criteria.append(SupportTicket.reporter_user_id == reporter_user_id)
        stmt = self.scoped_select(*criteria).order_by(SupportTicket.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def count_tickets(
        self,
        *,
        q: str | None = None,
        status: SupportTicketStatus | None = None,
        category: SupportTicketCategory | None = None,
        reporter_user_id: UUID | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(SupportTicket).where(SupportTicket.tenant_id == self.tenant_id)
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(or_(SupportTicket.subject.ilike(pattern), SupportTicket.message.ilike(pattern)))
        if status is not None:
            stmt = stmt.where(SupportTicket.status == status)
        if category is not None:
            stmt = stmt.where(SupportTicket.category == category)
        if reporter_user_id is not None:
            stmt = stmt.where(SupportTicket.reporter_user_id == reporter_user_id)
        return int(self.db.execute(stmt).scalar_one())
