from __future__ import annotations

from uuid import UUID

from app.core.jobs import task
from app.services.webhook_service import WebhookService


@task(name="webhook.delivery", max_retries=0, retry_base_delay_seconds=1.0)
async def process_webhook_delivery_task(*, tenant_id: str, delivery_id: str) -> None:
    service = WebhookService(tenant_id=UUID(tenant_id), actor_user_id=None, actor_role="owner")
    await service.process_delivery(delivery_id=UUID(delivery_id))
