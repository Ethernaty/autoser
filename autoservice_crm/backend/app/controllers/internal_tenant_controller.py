from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query

from app.controllers.schemas.internal_tenant_schemas import (
    InternalForcePlanRequest,
    InternalTenantListResponse,
    InternalTenantResponse,
    InternalTenantStateRequest,
)
from app.core.internal_auth import require_internal_service_auth
from app.models.subscription import SubscriptionStatus
from app.models.tenant import TenantState
from app.services.subscription_service import SubscriptionService
from app.services.tenant_lifecycle_service import TenantLifecycleService


router = APIRouter(
    prefix="/internal/tenants",
    tags=["Internal Tenants"],
    dependencies=[Depends(require_internal_service_auth)],
)


def get_tenant_lifecycle_service() -> TenantLifecycleService:
    return TenantLifecycleService()


@router.get("", response_model=InternalTenantListResponse)
async def list_tenants(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: TenantLifecycleService = Depends(get_tenant_lifecycle_service),
) -> InternalTenantListResponse:
    tenants = await service.list_tenants(limit=limit, offset=offset)
    return InternalTenantListResponse(
        items=[InternalTenantResponse.model_validate(tenant) for tenant in tenants],
        limit=limit,
        offset=offset,
    )


@router.post("/{tenant_id}/suspend", response_model=InternalTenantResponse)
async def suspend_tenant(
    tenant_id: UUID,
    payload: InternalTenantStateRequest | None = None,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    lifecycle_service: TenantLifecycleService = Depends(get_tenant_lifecycle_service),
) -> InternalTenantResponse:
    _ = payload
    await lifecycle_service.set_tenant_state(tenant_id=tenant_id, state=TenantState.SUSPENDED)
    subscription_service = SubscriptionService(tenant_id=tenant_id, actor_user_id=None, actor_role="owner")
    await subscription_service.set_status(
        status=SubscriptionStatus.SUSPENDED,
        idempotency_key=idempotency_key,
        event_type="tenant.suspended",
    )
    tenant = await lifecycle_service.get_tenant(tenant_id=tenant_id)
    return InternalTenantResponse.model_validate(tenant)


@router.post("/{tenant_id}/resume", response_model=InternalTenantResponse)
async def resume_tenant(
    tenant_id: UUID,
    payload: InternalTenantStateRequest | None = None,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    lifecycle_service: TenantLifecycleService = Depends(get_tenant_lifecycle_service),
) -> InternalTenantResponse:
    _ = payload
    await lifecycle_service.set_tenant_state(tenant_id=tenant_id, state=TenantState.ACTIVE)
    subscription_service = SubscriptionService(tenant_id=tenant_id, actor_user_id=None, actor_role="owner")
    await subscription_service.set_status(
        status=SubscriptionStatus.ACTIVE,
        idempotency_key=idempotency_key,
        event_type="tenant.resumed",
    )
    tenant = await lifecycle_service.get_tenant(tenant_id=tenant_id)
    return InternalTenantResponse.model_validate(tenant)


@router.post("/{tenant_id}/force-plan", response_model=InternalTenantResponse)
async def force_plan(
    tenant_id: UUID,
    payload: InternalForcePlanRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    lifecycle_service: TenantLifecycleService = Depends(get_tenant_lifecycle_service),
) -> InternalTenantResponse:
    subscription_service = SubscriptionService(tenant_id=tenant_id, actor_user_id=None, actor_role="owner")
    await subscription_service.change_plan(
        plan_id=payload.plan_id,
        cancel_at_period_end=False,
        idempotency_key=idempotency_key,
    )
    tenant = await lifecycle_service.get_tenant(tenant_id=tenant_id)
    return InternalTenantResponse.model_validate(tenant)
