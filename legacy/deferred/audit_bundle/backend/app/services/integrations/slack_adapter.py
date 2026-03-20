from __future__ import annotations

from typing import Any

from app.services.integrations.base_adapter import BaseIntegrationAdapter, IntegrationSyncResult


class SlackAdapter(BaseIntegrationAdapter):
    """Slack integration adapter skeleton."""

    provider = "slack"

    async def outbound_sync(self, payload: dict[str, Any]) -> IntegrationSyncResult:
        credentials = await self.load_credentials(name="default")
        if credentials is None:
            return IntegrationSyncResult(success=False, details={"error": "slack_credentials_missing"})
        channel = str(payload.get("channel", "general"))
        return IntegrationSyncResult(
            success=True,
            details={"provider": self.provider, "channel": channel, "sent": True},
        )

    async def inbound_webhook(self, payload: dict[str, Any], headers: dict[str, str]) -> IntegrationSyncResult:
        event_type = str(payload.get("type", "unknown"))
        return IntegrationSyncResult(
            success=True,
            details={"provider": self.provider, "event_type": event_type, "headers_seen": len(headers)},
        )
