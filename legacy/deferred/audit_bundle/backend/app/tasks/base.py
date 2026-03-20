from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.tenant_scope import snapshot_scope


@dataclass(frozen=True)
class TaskContext:
    task_id: UUID
    tenant_id: UUID
    user_id: UUID | None
    role: str | None
    request_id: str | None
    correlation_id: str | None
    created_at: datetime

    @classmethod
    def from_current_scope(cls, *, tenant_id: UUID) -> "TaskContext":
        scope = snapshot_scope()
        return cls(
            task_id=uuid4(),
            tenant_id=tenant_id,
            user_id=scope.user_id,
            role=scope.role,
            request_id=scope.request_id,
            correlation_id=scope.correlation_id,
            created_at=datetime.now(UTC),
        )
