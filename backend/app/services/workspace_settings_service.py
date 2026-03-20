from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.core.input_security import sanitize_text
from app.models.workspace_settings import WorkspaceSettings
from app.repositories.tenant_repository import TenantRepository
from app.repositories.workspace_settings_repository import WorkspaceSettingsRepository
from app.services.base_service import BaseService


class WorkspaceSettingsService(BaseService):
    def __init__(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
        )

    async def get_settings(self) -> WorkspaceSettings:
        def write_op(db: Session) -> WorkspaceSettings:
            repo = WorkspaceSettingsRepository(db=db, tenant_id=self.tenant_id)
            current = repo.get_current()
            if current is not None:
                return current

            tenant_repo = TenantRepository(db)
            tenant = tenant_repo.get_by_id(self.tenant_id)
            if tenant is None:
                raise AppError(status_code=404, code="workspace_not_found", message="Workspace not found")

            return repo.create(
                service_name=tenant.name,
                phone="",
                address=None,
                timezone="UTC",
                currency="USD",
                working_hours_note=None,
            )

        return await self.execute_write(write_op, idempotent=False)

    async def update_settings(
        self,
        *,
        service_name: str | None = None,
        phone: str | None = None,
        address: str | None = None,
        timezone: str | None = None,
        currency: str | None = None,
        working_hours_note: str | None = None,
    ) -> WorkspaceSettings:
        updates: dict[str, object] = {}
        if service_name is not None:
            updates["service_name"] = self._normalize_required(service_name, field="service_name", max_length=200)
        if phone is not None:
            updates["phone"] = self._normalize_required(phone, field="phone", max_length=20)
        if address is not None:
            updates["address"] = self._normalize_optional(address, max_length=300)
        if timezone is not None:
            updates["timezone"] = self._normalize_required(timezone, field="timezone", max_length=64)
        if currency is not None:
            updates["currency"] = self._normalize_required(currency, field="currency", max_length=8).upper()
        if working_hours_note is not None:
            updates["working_hours_note"] = self._normalize_optional(working_hours_note, max_length=2000)

        if not updates:
            raise AppError(status_code=400, code="empty_update", message="No fields provided for update")

        def write_op(db: Session) -> WorkspaceSettings:
            repo = WorkspaceSettingsRepository(db=db, tenant_id=self.tenant_id)
            current = repo.get_current()
            if current is None:
                tenant_repo = TenantRepository(db)
                tenant = tenant_repo.get_by_id(self.tenant_id)
                if tenant is None:
                    raise AppError(status_code=404, code="workspace_not_found", message="Workspace not found")
                current = repo.create(
                    service_name=tenant.name,
                    phone="",
                    address=None,
                    timezone="UTC",
                    currency="USD",
                    working_hours_note=None,
                )
            return repo.update(current, **updates)

        return await self.execute_write(write_op, idempotent=False)

    @staticmethod
    def _normalize_required(value: str, *, field: str, max_length: int) -> str:
        normalized = sanitize_text(value, max_length=max_length)
        if not normalized:
            raise AppError(status_code=400, code=f"invalid_{field}", message=f"Invalid {field}")
        return normalized

    @staticmethod
    def _normalize_optional(value: str | None, *, max_length: int) -> str | None:
        if value is None:
            return None
        normalized = sanitize_text(value, max_length=max_length)
        return normalized if normalized else None
