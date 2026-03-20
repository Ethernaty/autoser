from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.services.integration_service import IntegrationCredentialService


@dataclass(frozen=True)
class IntegrationSyncResult:
    success: bool
    details: dict[str, Any]


class BaseIntegrationAdapter(ABC):
    """Base adapter contract for third-party integrations."""

    provider: str

    def __init__(self, *, tenant_id: UUID, credentials_service: IntegrationCredentialService) -> None:
        self.tenant_id = tenant_id
        self.credentials_service = credentials_service

    @abstractmethod
    async def outbound_sync(self, payload: dict[str, Any]) -> IntegrationSyncResult:
        """Push outbound data to integration provider."""

    @abstractmethod
    async def inbound_webhook(self, payload: dict[str, Any], headers: dict[str, str]) -> IntegrationSyncResult:
        """Process inbound webhook callback from integration provider."""

    async def store_credentials(self, *, name: str, credentials: dict[str, Any]) -> None:
        await self.credentials_service.store_credentials(
            provider=self.provider,
            name=name,
            credentials=credentials,
        )

    async def load_credentials(self, *, name: str) -> dict[str, Any] | None:
        entity = await self.credentials_service.load_credentials(provider=self.provider, name=name)
        if entity is None or not entity.is_active:
            return None
        return dict(entity.credentials)
