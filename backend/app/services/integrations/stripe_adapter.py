from __future__ import annotations

from typing import Any

from app.services.integrations.base_adapter import BaseIntegrationAdapter, IntegrationSyncResult


class StripeAdapter(BaseIntegrationAdapter):
    """Stripe integration adapter skeleton."""

    provider = "stripe"

    async def outbound_sync(self, payload: dict[str, Any]) -> IntegrationSyncResult:
        credentials = await self.load_credentials(name="default")
        if credentials is None:
            return IntegrationSyncResult(success=False, details={"error": "stripe_credentials_missing"})
        return IntegrationSyncResult(
            success=True,
            details={
                "provider": self.provider,
                "synced": True,
                "payload_keys": sorted(payload.keys()),
            },
        )

    async def inbound_webhook(self, payload: dict[str, Any], headers: dict[str, str]) -> IntegrationSyncResult:
        event_type = str(payload.get("type", "unknown"))
        signature = headers.get("stripe-signature")
        if not signature:
            return IntegrationSyncResult(success=False, details={"error": "missing_signature"})
        return IntegrationSyncResult(
            success=True,
            details={"provider": self.provider, "event_type": event_type},
        )
