from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.subscription import SubscriptionStatus


class PlanResponse(BaseModel):
    id: UUID
    name: str
    price: Decimal
    limits: dict[str, object]
    features: dict[str, object]
    is_active: bool
    description: str | None = None


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    plan_id: UUID
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    trial_end: datetime | None
    created_at: datetime
    updated_at: datetime


class SubscriptionChangePlanRequest(BaseModel):
    plan_id: UUID
    cancel_at_period_end: bool = False


class SubscriptionCancelRequest(BaseModel):
    cancel_at_period_end: bool = True


class FeatureCheckResponse(BaseModel):
    feature: str
    enabled: bool


class UsageQuotaResponse(BaseModel):
    resource: str
    used: int
    hard_limit: int
    remaining: int
    soft_warning: bool
    period_start: date


class BillingEventResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    type: str
    payload: dict[str, object]
    created_at: datetime
