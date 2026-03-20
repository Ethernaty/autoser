from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.services.audit_log_query_service import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    AuditLogPage,
    AuditLogQueryService,
)


@dataclass(frozen=True)
class MonitoringRowView:
    id: UUID
    created_at: datetime
    level: str
    action: str
    entity: str
    user_id: UUID
    message: str
    stacktrace: str | None


@dataclass(frozen=True)
class MonitoringPageView:
    rows: list[MonitoringRowView]
    q: str
    level: str
    page: int
    per_page: int
    has_prev: bool
    has_next: bool
    auto_refresh: bool
    errors_only: bool


class MonitoringAdminService:
    """Presentation-level orchestration for logs/errors monitoring pages."""

    async def build_logs_page(
        self,
        *,
        tenant_id: UUID,
        q: str,
        level: str,
        page: int,
        per_page: int,
        auto_refresh: bool,
        errors_only: bool,
    ) -> MonitoringPageView:
        normalized_page = max(1, page)
        normalized_per_page = max(1, min(per_page, MAX_LIMIT))
        normalized_query = q.strip()
        normalized_level = self.normalize_level(level)

        offset = (normalized_page - 1) * normalized_per_page
        query_service = AuditLogQueryService(tenant_id=tenant_id)
        result = await query_service.list_latest_logs(
            limit=normalized_per_page,
            offset=offset,
            level=normalized_level if not errors_only else "ERROR",
            search=normalized_query or None,
            errors_only=errors_only,
        )

        return MonitoringPageView(
            rows=self._to_rows(result),
            q=normalized_query,
            level=("ERROR" if errors_only else normalized_level),
            page=normalized_page,
            per_page=normalized_per_page,
            has_prev=normalized_page > 1,
            has_next=result.has_next,
            auto_refresh=auto_refresh,
            errors_only=errors_only,
        )

    @staticmethod
    def normalize_level(level: str | None) -> str:
        if not level:
            return ""
        normalized = level.strip().upper()
        aliases = {"WARN": "WARNING", "ERR": "ERROR", "FATAL": "CRITICAL"}
        normalized = aliases.get(normalized, normalized)
        return normalized if normalized in {"", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"} else ""

    @staticmethod
    def _to_rows(page: AuditLogPage) -> list[MonitoringRowView]:
        rows: list[MonitoringRowView] = []
        for item in page.items:
            rows.append(
                MonitoringRowView(
                    id=item.id,
                    created_at=item.created_at,
                    level=item.level,
                    action=item.action,
                    entity=item.entity,
                    user_id=item.user_id,
                    message=item.message,
                    stacktrace=item.stacktrace,
                )
            )
        return rows


DEFAULT_PER_PAGE = DEFAULT_LIMIT
MAX_PER_PAGE = MAX_LIMIT
