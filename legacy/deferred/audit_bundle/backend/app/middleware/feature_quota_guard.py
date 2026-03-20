from __future__ import annotations

from fastapi import Depends

from app.core.exceptions import AppError
from app.core.request_context import UserRequestContext, get_current_user_context
from app.services.feature_flag_service import FeatureFlagService
from app.services.usage_quota_service import UsageQuotaService


class RequireFeature:
    """FastAPI dependency to enforce tenant feature flags."""

    def __init__(self, feature_name: str):
        self.feature_name = feature_name

    async def __call__(self, context: UserRequestContext = Depends(get_current_user_context)) -> UserRequestContext:
        service = FeatureFlagService(
            tenant_id=context.tenant_id,
            actor_user_id=context.user_id,
            actor_role=context.role,
        )
        enabled = await service.has_feature(feature_name=self.feature_name, default=False)
        if not enabled:
            raise AppError(
                status_code=402,
                code="feature_not_available",
                message="Feature is not available for this tenant plan",
                details={"feature": self.feature_name},
            )
        return context


class RequireQuota:
    """FastAPI dependency to enforce tenant quotas."""

    def __init__(self, resource: str, amount: int = 1):
        self.resource = resource
        self.amount = amount

    async def __call__(self, context: UserRequestContext = Depends(get_current_user_context)) -> UserRequestContext:
        service = UsageQuotaService(
            tenant_id=context.tenant_id,
            actor_user_id=context.user_id,
            actor_role=context.role,
        )
        await service.track_usage(resource=self.resource, amount=self.amount)
        return context
