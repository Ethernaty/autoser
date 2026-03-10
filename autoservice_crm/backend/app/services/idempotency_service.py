from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.idempotency_key import IdempotencyKey, IdempotencyStatus
from app.repositories.idempotency_repository import IdempotencyRepository
from app.services.base_service import BaseService


@dataclass
class IdempotencyDecision:
    proceed: bool
    record_id: UUID | None = None
    response_payload: dict[str, Any] | None = None


class IdempotencyService:
    """Production-safe idempotency coordinator using DB storage."""

    def __init__(self, base_service: BaseService):
        self._base_service = base_service
        self._ttl_seconds = max(60, base_service._settings.idempotency_ttl_seconds)

    @staticmethod
    def build_request_hash(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    async def begin(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        route: str,
        key: str,
        request_hash: str,
    ) -> IdempotencyDecision:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self._ttl_seconds)

        def write_op(db: Session) -> IdempotencyDecision:
            repo = IdempotencyRepository(db=db, tenant_id=tenant_id)
            repo.cleanup_expired()

            current = repo.get_for_scope(actor_id=actor_id, route=route, key=key)
            if current is None:
                try:
                    record = repo.reserve(
                        actor_id=actor_id,
                        route=route,
                        key=key,
                        request_hash=request_hash,
                        expires_at=expires_at,
                    )
                    return IdempotencyDecision(proceed=True, record_id=record.id)
                except IntegrityError:
                    current = repo.get_for_scope(actor_id=actor_id, route=route, key=key)

            if current is None:
                raise AppError(status_code=503, code="idempotency_unavailable", message="Idempotency unavailable")

            if current.expires_at < now:
                db.delete(current)
                db.flush()
                record = repo.reserve(
                    actor_id=actor_id,
                    route=route,
                    key=key,
                    request_hash=request_hash,
                    expires_at=expires_at,
                )
                return IdempotencyDecision(proceed=True, record_id=record.id)

            if current.request_hash != request_hash:
                raise AppError(
                    status_code=409,
                    code="idempotency_conflict",
                    message="Idempotency key already used with different payload",
                )

            if current.status == IdempotencyStatus.SUCCEEDED.value and current.response_payload is not None:
                return IdempotencyDecision(proceed=False, response_payload=current.response_payload)

            if current.status == IdempotencyStatus.PROCESSING.value:
                raise AppError(
                    status_code=409,
                    code="idempotency_in_progress",
                    message="Request with this idempotency key is still processing",
                )

            current.status = IdempotencyStatus.PROCESSING.value
            current.response_payload = None
            current.expires_at = expires_at
            db.flush()
            return IdempotencyDecision(proceed=True, record_id=current.id)

        return await self._base_service.execute_write(write_op, idempotent=True)

    async def mark_succeeded(self, *, tenant_id: UUID, record_id: UUID, response_payload: dict[str, Any]) -> None:
        safe_payload = json.loads(json.dumps(response_payload, default=str))

        def write_op(db: Session) -> None:
            repo = IdempotencyRepository(db=db, tenant_id=tenant_id)
            repo.mark_succeeded(record_id=record_id, response_payload=safe_payload)

        await self._base_service.execute_write(write_op, idempotent=True)

    async def mark_failed(self, *, tenant_id: UUID, record_id: UUID) -> None:
        def write_op(db: Session) -> None:
            repo = IdempotencyRepository(db=db, tenant_id=tenant_id)
            repo.mark_failed(record_id=record_id)

        await self._base_service.execute_write(write_op, idempotent=True)
