from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.integration_credential import IntegrationCredential
from app.repositories.base import BaseRepositoryTenantScoped


class IntegrationCredentialRepository(BaseRepositoryTenantScoped[IntegrationCredential]):
    """Tenant-scoped integration credential repository."""

    def __init__(self, db: Session, tenant_id: UUID | None = None):
        super().__init__(db=db, model=IntegrationCredential, tenant_id=tenant_id)

    def get_by_provider_name(self, *, provider: str, name: str) -> IntegrationCredential | None:
        stmt = self.scoped_select(
            IntegrationCredential.provider == provider,
            IntegrationCredential.name == name,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert_credentials(
        self,
        *,
        provider: str,
        name: str,
        credentials: dict[str, Any],
    ) -> IntegrationCredential:
        existing = self.get_by_provider_name(provider=provider, name=name)
        if existing is None:
            return self.create(
                provider=provider,
                name=name,
                credentials=credentials,
                is_active=True,
            )
        existing.credentials = credentials
        existing.is_active = True
        self.db.flush()
        return existing

    def deactivate(self, *, provider: str, name: str) -> bool:
        entity = self.get_by_provider_name(provider=provider, name=name)
        if entity is None:
            return False
        entity.is_active = False
        self.db.flush()
        return True
