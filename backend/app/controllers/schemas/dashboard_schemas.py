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
