from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.cache import CacheBackend, get_cache_backend
from app.core.database import SessionLocal
from app.core.serialization import JsonSerializer, Serializer
from app.models.integration_credential import IntegrationCredential
from app.repositories.integration_credential_repository import IntegrationCredentialRepository
from app.services.base_service import BaseService


class IntegrationCredentialService(BaseService):
    """Tenant-scoped integration credential storage service."""

    def __init__(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None = None,
        actor_role: str | None = None,
        session_factory: sessionmaker[Session] | None = None,
        serializer: Serializer | None = None,
        cache_backend: CacheBackend | None = None,
    ) -> None:
        self.actor_role = (actor_role or "").lower() if actor_role else None
        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
            serializer=serializer or JsonSerializer(),
            cache_backend=cache_backend or get_cache_backend(),
        )

    async def store_credentials(
        self,
        *,
        provider: str,
        name: str,
        credentials: dict[str, Any],
    ) -> IntegrationCredential:
        normalized_provider = provider.strip().lower()
        normalized_name = name.strip().lower()

        def write_op(db: Session) -> IntegrationCredential:
            repo = IntegrationCredentialRepository(db=db, tenant_id=self.tenant_id)
            return repo.upsert_credentials(
                provider=normalized_provider,
                name=normalized_name,
                credentials=credentials,
            )

        return await self.execute_write(write_op, idempotent=True)

    async def load_credentials(self, *, provider: str, name: str) -> IntegrationCredential | None:
        normalized_provider = provider.strip().lower()
        normalized_name = name.strip().lower()

        def read_op(db: Session) -> IntegrationCredential | None:
            repo = IntegrationCredentialRepository(db=db, tenant_id=self.tenant_id)
            return repo.get_by_provider_name(provider=normalized_provider, name=normalized_name)

        return await self.execute_read(read_op)
