from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Text, String, cast, func, or_
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from app.core.database import SessionLocal
from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository


DEFAULT_LIMIT = 25
MAX_LIMIT = 100


@dataclass(frozen=True)
class AuditLogRecord:
    id: UUID
    user_id: UUID
    action: str
    entity: str
    entity_id: UUID | None
    created_at: datetime
    level: str
    message: str
    stacktrace: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class AuditLogPage:
    items: list[AuditLogRecord]
    limit: int
    offset: int
    has_next: bool


class AuditLogQueryService:
    """Read-only audit log query service for monitoring UIs."""

    def __init__(
        self,
        *,
        tenant_id: UUID,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self._session_factory = session_factory or SessionLocal

    async def list_latest_logs(
        self,
        *,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        level: str | None = None,
        search: str | None = None,
        errors_only: bool = False,
    ) -> AuditLogPage:
        safe_limit = max(1, min(limit, MAX_LIMIT))
        safe_offset = max(0, offset)

        rows = await run_in_threadpool(
            self._list_latest_logs_sync,
            safe_limit,
            safe_offset,
            level,
            search,
            errors_only,
        )

        has_next = len(rows) > safe_limit
        page_rows = rows[:safe_limit]
        return AuditLogPage(
            items=[self._to_record(row) for row in page_rows],
            limit=safe_limit,
            offset=safe_offset,
            has_next=has_next,
        )

    def _list_latest_logs_sync(
        self,
        limit: int,
        offset: int,
        level: str | None,
        search: str | None,
        errors_only: bool,
    ) -> list[AuditLog]:
        with self._session_factory() as db:
            with db.begin():
                repo = AuditLogRepository(db=db, tenant_id=self.tenant_id)
                stmt = repo.scoped_select()

                if search and search.strip():
                    normalized = search.strip().lower()
                    like_pattern = f"%{normalized}%"
                    raw_pattern = f"%{search.strip()}%"
                    stmt = stmt.where(
                        or_(
                            func.lower(AuditLog.action).like(like_pattern),
                            func.lower(AuditLog.entity).like(like_pattern),
                            cast(AuditLog.user_id, String).ilike(raw_pattern),
                            cast(AuditLog.entity_id, String).ilike(raw_pattern),
                        )
                    )

                level_filter = self._normalize_level(level)
                if errors_only:
                    stmt = stmt.where(self._error_predicate())
                elif level_filter:
                    stmt = stmt.where(self._level_predicate(level_filter))

                stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit + 1).offset(offset)
                return list(db.execute(stmt).scalars().all())

    @staticmethod
    def _normalize_level(level: str | None) -> str | None:
        if not level:
            return None
        normalized = level.strip().upper()
        aliases = {
            "WARN": "WARNING",
            "ERR": "ERROR",
            "FATAL": "CRITICAL",
        }
        normalized = aliases.get(normalized, normalized)
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        return normalized if normalized in allowed else None

    @staticmethod
    def _level_predicate(level: str):
        metadata_level = func.lower(AuditLog.metadata_json["level"].astext)
        metadata_severity = func.lower(AuditLog.metadata_json["severity"].astext)
        metadata_log_level = func.lower(AuditLog.metadata_json["log_level"].astext)

        lvl = level.lower()
        if lvl == "warning":
            return or_(
                metadata_level.in_(["warning", "warn"]),
                metadata_severity.in_(["warning", "warn"]),
                metadata_log_level.in_(["warning", "warn"]),
                func.lower(AuditLog.action).like("%warn%"),
            )
        if lvl == "error":
            return AuditLogQueryService._error_predicate()
        if lvl == "critical":
            return or_(
                metadata_level.in_(["critical", "fatal"]),
                metadata_severity.in_(["critical", "fatal"]),
                metadata_log_level.in_(["critical", "fatal"]),
                func.lower(AuditLog.action).like("%critical%"),
                func.lower(AuditLog.action).like("%fatal%"),
            )

        return or_(
            metadata_level == lvl,
            metadata_severity == lvl,
            metadata_log_level == lvl,
            func.lower(AuditLog.action).like(f"%{lvl}%"),
        )

    @staticmethod
    def _error_predicate():
        metadata_level = func.lower(AuditLog.metadata_json["level"].astext)
        metadata_severity = func.lower(AuditLog.metadata_json["severity"].astext)
        metadata_log_level = func.lower(AuditLog.metadata_json["log_level"].astext)
        metadata_text = cast(AuditLog.metadata_json, Text)

        return or_(
            metadata_level.in_(["error", "critical", "fatal"]),
            metadata_severity.in_(["error", "critical", "fatal"]),
            metadata_log_level.in_(["error", "critical", "fatal"]),
            func.lower(AuditLog.action).like("%error%"),
            func.lower(AuditLog.action).like("%exception%"),
            func.lower(AuditLog.action).like("%fail%"),
            metadata_text.ilike("%traceback%"),
            metadata_text.ilike("%stacktrace%"),
            metadata_text.ilike("%exception%"),
        )

    def _to_record(self, row: AuditLog) -> AuditLogRecord:
        metadata = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        level = self._infer_level(action=row.action, metadata=metadata)
        message = self._extract_message(action=row.action, metadata=metadata)
        stacktrace = self._extract_stacktrace(metadata)

        return AuditLogRecord(
            id=row.id,
            user_id=row.user_id,
            action=row.action,
            entity=row.entity,
            entity_id=row.entity_id,
            created_at=row.created_at,
            level=level,
            message=message,
            stacktrace=stacktrace,
            metadata=metadata,
        )

    @staticmethod
    def _infer_level(*, action: str, metadata: dict[str, Any]) -> str:
        for key in ("level", "severity", "log_level"):
            value = metadata.get(key)
            if isinstance(value, str):
                normalized = value.strip().upper()
                if normalized == "WARN":
                    normalized = "WARNING"
                if normalized == "FATAL":
                    normalized = "CRITICAL"
                if normalized in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
                    return normalized

        action_l = action.lower()
        if any(token in action_l for token in ("error", "exception", "fail", "critical", "fatal")):
            return "ERROR"
        if "warn" in action_l:
            return "WARNING"
        return "INFO"

    @staticmethod
    def _extract_message(*, action: str, metadata: dict[str, Any]) -> str:
        for key in ("message", "detail", "reason", "error", "summary"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:400]

        error_obj = metadata.get("error")
        if isinstance(error_obj, dict):
            message = error_obj.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()[:400]

        return action

    @staticmethod
    def _extract_stacktrace(metadata: dict[str, Any]) -> str | None:
        for key in ("stacktrace", "traceback", "error_stack", "exception_stack", "stack"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value[:8000]

        error_obj = metadata.get("error")
        if isinstance(error_obj, dict):
            for key in ("stacktrace", "traceback", "stack"):
                value = error_obj.get(key)
                if isinstance(value, str) and value.strip():
                    return value[:8000]

        return None


