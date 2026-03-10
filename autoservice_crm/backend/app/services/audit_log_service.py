from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from app.core.database import SessionLocal
from app.repositories.audit_log_repository import AuditLogRepository


class AuditLogService:
    """Application service for recording audit logs."""

    def __init__(
        self,
        tenant_id: UUID,
        db: Session | None = None,
        session_factory: sessionmaker[Session] | None = None,
    ):
        self.tenant_id = tenant_id
        self._provided_db = db
        self._session_factory = session_factory or SessionLocal

    async def log_action(
        self,
        *,
        user_id: UUID,
        action: str,
        entity: str,
        entity_id: UUID | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Persist audit event.

        This method intentionally swallows all failures to avoid breaking
        the primary business transaction flow.
        """

        def run() -> None:
            db = self._provided_db or self._session_factory()
            owns_session = self._provided_db is None
            transaction = None
            try:
                if owns_session:
                    transaction = db.begin()

                repo = AuditLogRepository(db=db, tenant_id=self.tenant_id)
                repo.create_log(
                    user_id=user_id,
                    action=action,
                    entity=entity,
                    entity_id=entity_id,
                    metadata=metadata or {},
                )

                if transaction is not None:
                    transaction.commit()
            except Exception:
                if transaction is not None:
                    transaction.rollback()
                logger = logging.getLogger(__name__)
                logger.exception("Failed to write audit log", extra={"tenant_id": str(self.tenant_id)})
                return None
            finally:
                if owns_session:
                    db.close()

        await run_in_threadpool(run)
