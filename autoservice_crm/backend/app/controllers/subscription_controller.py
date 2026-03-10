from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query

from app.controllers.schemas.subscription_schemas import (
    BillingEventResponse,
    FeatureCheckResponse,
    PlanResponse,
    SubscriptionCancelRequest,
    SubscriptionChangePlanRequest,
    SubscriptionResponse,
    UsageQuotaResponse,
)
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.services.feature_flag_service import FeatureFlagService
from app.services.subscription_service import SubscriptionService
from app.services.usage_quota_service import UsageQuotaService


router = APIRouter(prefix="/subscription", tags=["Subscription"])


def get_subscription_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> SubscriptionService:
    return SubscriptionService(
        tenant_id=tenant_id,
        actor_user_id=context.user_id,
        actor_role=context.role,
    )


def get_feature_flag_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> FeatureFlagService:
    return FeatureFlagService(
        tenant_id=tenant_id,
        actor_user_id=context.user_id,
        actor_role=context.role,
    )


def get_usage_quota_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> UsageQuotaService:
    return UsageQuotaService(
        tenant_id=tenant_id,
        actor_user_id=context.user_id,
        actor_role=context.role,
    )


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(service: SubscriptionService = Depends(get_subscription_service)) -> SubscriptionResponse:
    subscription = await service.get_current_subscription()
    return SubscriptionResponse.model_validate(subscription)


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(service: SubscriptionService = Depends(get_subscription_service)) -> list[PlanResponse]:
    plans = await service.list_active_plans()
    return [
        PlanResponse(
            id=plan.id,
            name=plan.name,
            price=plan.price,
            limits=dict(plan.limits_json or {}),
            features=dict(plan.features_json or {}),
            is_active=plan.is_active,
            description=plan.description,
        )
        for plan in plans
    ]


@router.post("/change-plan", response_model=SubscriptionResponse)
async def change_plan(
    payload: SubscriptionChangePlanRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    subscription = await service.change_plan(
        plan_id=payload.plan_id,
        cancel_at_period_end=payload.cancel_at_period_end,
        idempotency_key=idempotency_key,
    )
    return SubscriptionResponse.model_validate(subscription)


@router.post("/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    payload: SubscriptionCancelRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    subscription = await service.cancel_subscription(
        cancel_at_period_end=payload.cancel_at_period_end,
        idempotency_key=idempotency_key,
    )
    return SubscriptionResponse.model_validate(subscription)


@router.get("/features/{feature_name}", response_model=FeatureCheckResponse)
async def has_feature(
    feature_name: str,
    service: FeatureFlagService = Depends(get_feature_flag_service),
) -> FeatureCheckResponse:
    enabled = await service.has_feature(feature_name=feature_name, default=False)
    return FeatureCheckResponse(feature=feature_name, enabled=enabled)


@router.get("/usage/{resource}", response_model=UsageQuotaResponse)
async def get_usage(resource: str, service: UsageQuotaService = Depends(get_usage_quota_service)) -> UsageQuotaResponse:
    usage = await service.get_usage(resource=resource)
    return UsageQuotaResponse(
        resource=usage.resource,
        used=usage.used,
        hard_limit=usage.hard_limit,
        remaining=usage.remaining,
        soft_warning=usage.soft_warning,
        period_start=usage.period_start,
    )


@router.get("/events", response_model=list[BillingEventResponse])
async def list_billing_events(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: SubscriptionService = Depends(get_subscription_service),
) -> list[BillingEventResponse]:
    events = await service.list_billing_events(limit=limit, offset=offset)
    return [BillingEventResponse.model_validate(event) for event in events]
