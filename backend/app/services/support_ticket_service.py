from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.core.input_security import sanitize_text
from app.models.support_ticket import SupportTicket, SupportTicketCategory, SupportTicketStatus
from app.repositories.support_ticket_repository import SupportTicketRepository
from app.services.base_service import BaseService


class SupportTicketService(BaseService):
    def __init__(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None = None,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        self.actor_role = (actor_role or "").lower() if actor_role else None
        self.max_limit = get_settings().max_limit
        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
        )

    async def create_ticket(
        self,
        *,
        subject: str,
        category: SupportTicketCategory | str = SupportTicketCategory.GENERAL,
        message: str,
    ) -> SupportTicket:
        if self.actor_user_id is None:
            raise AppError(status_code=401, code="actor_required", message="Authenticated actor is required")

        normalized_subject = self._normalize_subject(subject)
        normalized_category = self._normalize_category(category)
        normalized_message = self._normalize_message(message)

        def write_op(db: Session) -> SupportTicket:
            repo = SupportTicketRepository(db=db, tenant_id=self.tenant_id)
            return repo.create(
                reporter_user_id=self.actor_user_id,
                subject=normalized_subject,
                category=normalized_category,
                message=normalized_message,
                status=SupportTicketStatus.OPEN,
            )

        return await self.execute_write(write_op, idempotent=False)

    async def list_tickets(
        self,
        *,
        limit: int,
        offset: int,
        q: str | None = None,
        status: SupportTicketStatus | str | None = None,
        category: SupportTicketCategory | str | None = None,
        my_only: bool = False,
    ) -> tuple[list[SupportTicket], int]:
        self._validate_pagination(limit=limit, offset=offset)
        normalized_status = self._normalize_status(status)
        normalized_category = self._normalize_category(category) if category is not None else None
        normalized_query = sanitize_text(q or "", max_length=120) or None
        reporter_user_id = self.actor_user_id if my_only else None

        def read_op(db: Session) -> tuple[list[SupportTicket], int]:
            repo = SupportTicketRepository(db=db, tenant_id=self.tenant_id)
            items = repo.list_tickets(
                limit=limit,
                offset=offset,
                q=normalized_query,
                status=normalized_status,
                category=normalized_category,
                reporter_user_id=reporter_user_id,
            )
            total = repo.count_tickets(
                q=normalized_query,
                status=normalized_status,
                category=normalized_category,
                reporter_user_id=reporter_user_id,
            )
            return items, total

        return await self.execute_read(read_op)

    async def update_status(self, *, ticket_id: UUID, status: SupportTicketStatus | str) -> SupportTicket:
        normalized_status = self._normalize_status(status)
        if normalized_status is None:
            raise AppError(status_code=400, code="invalid_status", message="Invalid support ticket status")

        def write_op(db: Session) -> SupportTicket:
            repo = SupportTicketRepository(db=db, tenant_id=self.tenant_id)
            ticket = repo.get_by_id(ticket_id)
            if ticket is None:
                raise AppError(status_code=404, code="support_ticket_not_found", message="Support ticket not found")
            ticket.status = normalized_status
            db.flush()
            db.refresh(ticket)
            return ticket

        return await self.execute_write(write_op, idempotent=False)

    async def add_message(self, *, ticket_id: UUID, message: str) -> SupportTicket:
        if self.actor_user_id is None:
            raise AppError(status_code=401, code="actor_required", message="Authenticated actor is required")
        normalized_message = self._normalize_message(message)

        def write_op(db: Session) -> SupportTicket:
            repo = SupportTicketRepository(db=db, tenant_id=self.tenant_id)
            ticket = repo.get_by_id(ticket_id)
            if ticket is None:
                raise AppError(status_code=404, code="support_ticket_not_found", message="Support ticket not found")
            ticket.messages = [
                *(ticket.messages or []),
                {
                    "id": str(uuid4()),
                    "author_user_id": str(self.actor_user_id),
                    "author_role": self.actor_role or "employee",
                    "message": normalized_message,
                    "created_at": datetime.now(UTC).isoformat(),
                },
            ]
            if ticket.status in {SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED}:
                ticket.status = SupportTicketStatus.IN_PROGRESS
            db.flush()
            db.refresh(ticket)
            return ticket

        return await self.execute_write(write_op, idempotent=False)

    @staticmethod
    def _normalize_subject(value: str) -> str:
        normalized = sanitize_text(value, max_length=160)
        if not normalized:
            raise AppError(status_code=400, code="invalid_subject", message="Subject is required")
        return normalized

    @staticmethod
    def _normalize_message(value: str) -> str:
        normalized = sanitize_text(value, max_length=6000)
        if not normalized:
            raise AppError(status_code=400, code="invalid_message", message="Message is required")
        return normalized

    @staticmethod
    def _normalize_category(value: SupportTicketCategory | str | None) -> SupportTicketCategory:
        if value is None:
            return SupportTicketCategory.GENERAL
        if isinstance(value, SupportTicketCategory):
            return value
        try:
            return SupportTicketCategory(str(value).strip().lower())
        except Exception as exc:
            raise AppError(status_code=400, code="invalid_category", message="Invalid support ticket category") from exc

    @staticmethod
    def _normalize_status(value: SupportTicketStatus | str | None) -> SupportTicketStatus | None:
        if value is None:
            return None
        if isinstance(value, SupportTicketStatus):
            return value
        try:
            return SupportTicketStatus(str(value).strip().lower())
        except Exception as exc:
            raise AppError(status_code=400, code="invalid_status", message="Invalid support ticket status") from exc

    def _validate_pagination(self, *, limit: int, offset: int) -> None:
        if limit <= 0 or limit > self.max_limit or offset < 0:
            raise AppError(
                status_code=400,
                code="invalid_pagination",
                message=f"Pagination must satisfy 0 < limit <= {self.max_limit} and offset >= 0",
            )
