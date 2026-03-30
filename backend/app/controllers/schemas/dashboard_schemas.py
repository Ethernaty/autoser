from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class RecentActivityItem(BaseModel):
    id: UUID
    entity: str
    entity_id: UUID | None
    action: str
    user_id: UUID
    created_at: datetime


class DashboardSummaryResponse(BaseModel):
    open_work_orders_count: int
    closed_work_orders_count: int
    revenue_total: Decimal
    recent_activity: list[RecentActivityItem]


class AnalyticsMonthlyLoadItem(BaseModel):
    period: str
    orders_count: int
    clients_count: int


class AnalyticsRevenueItem(BaseModel):
    period: str
    paid_amount: Decimal
    order_amount: Decimal


class AnalyticsWeekdayLoadItem(BaseModel):
    weekday: str
    orders_count: int


class AnalyticsClientSourceItem(BaseModel):
    source: str
    clients_count: int


class AnalyticsPopularServiceItem(BaseModel):
    name: str
    usage_count: int


class AnalyticsProblemOrderItem(BaseModel):
    id: UUID
    description: str
    status: str
    remaining_amount: Decimal
    created_at: datetime


class DashboardAnalyticsResponse(BaseModel):
    generated_at: datetime
    clients_total: int
    work_orders_total: int
    open_work_orders_count: int
    closed_work_orders_count: int
    paid_amount_30d: Decimal
    unpaid_orders_count: int
    seasonality_monthly: list[AnalyticsMonthlyLoadItem]
    load_by_weekday: list[AnalyticsWeekdayLoadItem]
    revenue_monthly: list[AnalyticsRevenueItem]
    client_sources: list[AnalyticsClientSourceItem]
    popular_services: list[AnalyticsPopularServiceItem]
    problematic_orders: list[AnalyticsProblemOrderItem]
