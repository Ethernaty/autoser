from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.controllers.schemas.dashboard_schemas import (
    AnalyticsClientSourceItem,
    AnalyticsMonthlyLoadItem,
    AnalyticsPopularServiceItem,
    AnalyticsProblemOrderItem,
    AnalyticsRevenueItem,
    AnalyticsWeekdayLoadItem,
    DashboardAnalyticsResponse,
    DashboardSummaryResponse,
    RecentActivityItem,
)
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.middleware.permission_guard import RequirePermission
from app.services.work_order_service import WorkOrderService


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_work_order_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> WorkOrderService:
    return WorkOrderService(
        tenant_id=tenant_id,
        actor_user_id=context.user_id,
        actor_role=context.role,
    )


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    dependencies=[Depends(RequirePermission("orders", "read"))],
)
async def dashboard_summary(
    recent_limit: int = Query(default=10, ge=1, le=50),
    service: WorkOrderService = Depends(get_work_order_service),
) -> DashboardSummaryResponse:
    payload = await service.get_dashboard_summary(recent_limit=recent_limit)
    return DashboardSummaryResponse(
        open_work_orders_count=payload["open_work_orders_count"],
        closed_work_orders_count=payload["closed_work_orders_count"],
        revenue_total=payload["revenue_total"],
        recent_activity=[RecentActivityItem.model_validate(item) for item in payload["recent_activity"]],
    )


@router.get(
    "/analytics",
    response_model=DashboardAnalyticsResponse,
    dependencies=[Depends(RequirePermission("orders", "read"))],
)
async def dashboard_analytics(
    months: int = Query(default=12, ge=3, le=24),
    service: WorkOrderService = Depends(get_work_order_service),
) -> DashboardAnalyticsResponse:
    payload = await service.get_dashboard_analytics(months=months)
    return DashboardAnalyticsResponse(
        generated_at=payload["generated_at"],
        clients_total=payload["clients_total"],
        work_orders_total=payload["work_orders_total"],
        open_work_orders_count=payload["open_work_orders_count"],
        closed_work_orders_count=payload["closed_work_orders_count"],
        paid_amount_30d=payload["paid_amount_30d"],
        unpaid_orders_count=payload["unpaid_orders_count"],
        seasonality_monthly=[AnalyticsMonthlyLoadItem.model_validate(item) for item in payload["seasonality_monthly"]],
        load_by_weekday=[AnalyticsWeekdayLoadItem.model_validate(item) for item in payload["load_by_weekday"]],
        revenue_monthly=[AnalyticsRevenueItem.model_validate(item) for item in payload["revenue_monthly"]],
        client_sources=[AnalyticsClientSourceItem.model_validate(item) for item in payload["client_sources"]],
        popular_services=[AnalyticsPopularServiceItem.model_validate(item) for item in payload["popular_services"]],
        problematic_orders=[AnalyticsProblemOrderItem.model_validate(item) for item in payload["problematic_orders"]],
    )
