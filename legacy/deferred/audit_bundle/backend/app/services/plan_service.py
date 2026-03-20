from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.models.plan import Plan
from app.repositories.plan_repository import PlanRepository


@dataclass(frozen=True)
class PlanFeatureResult:
    enabled: bool
    source: str


class PlanService:
    """Plan lookup and validation service."""

    def __init__(self, *, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    async def get_plan(self, *, plan_id: UUID) -> Plan:
        plan = await run_in_threadpool(self._get_plan_sync, plan_id)
        if plan is None:
            raise AppError(status_code=404, code="plan_not_found", message="Plan not found")
        if not plan.is_active:
            raise AppError(status_code=409, code="plan_inactive", message="Plan is inactive")
        return plan

    async def get_plan_by_name(self, *, name: str) -> Plan:
        plan = await run_in_threadpool(self._get_plan_by_name_sync, name.strip().lower())
        if plan is None:
            raise AppError(status_code=404, code="plan_not_found", message="Plan not found")
        if not plan.is_active:
            raise AppError(status_code=409, code="plan_inactive", message="Plan is inactive")
        return plan

    async def list_active_plans(self) -> list[Plan]:
        return await run_in_threadpool(self._list_active_sync)

    @staticmethod
    def has_feature(plan: Plan, feature_name: str, default: bool = False) -> PlanFeatureResult:
        normalized = feature_name.strip().lower()
        if not normalized:
            return PlanFeatureResult(enabled=default, source="default")

        value = (plan.features_json or {}).get(normalized)
        if isinstance(value, bool):
            return PlanFeatureResult(enabled=value, source="plan")
        if isinstance(value, (int, float)):
            return PlanFeatureResult(enabled=bool(value), source="plan")
        return PlanFeatureResult(enabled=default, source="default")

    @staticmethod
    def resolve_limit(plan: Plan, resource: str, default: int) -> int:
        normalized = resource.strip().lower()
        if not normalized:
            return max(1, default)
        value = (plan.limits_json or {}).get(normalized)
        if isinstance(value, (int, float)):
            return max(1, int(value))
        if isinstance(value, dict):
            hard_limit = value.get("hard_limit", value.get("limit"))
            if isinstance(hard_limit, (int, float)):
                return max(1, int(hard_limit))
        return max(1, default)

    @staticmethod
    def resolve_burst_limit(plan: Plan, resource: str, default: int) -> int:
        normalized = resource.strip().lower()
        value = (plan.limits_json or {}).get(normalized)
        if isinstance(value, dict):
            burst = value.get("burst_limit")
            if isinstance(burst, (int, float)):
                return max(1, int(burst))
        return max(1, default)

    @staticmethod
    def resolve_warning_ratio(plan: Plan, resource: str, default: float) -> float:
        normalized = resource.strip().lower()
        value = (plan.limits_json or {}).get(normalized)
        if isinstance(value, dict):
            ratio = value.get("warning_ratio", value.get("soft_warning_ratio"))
            if isinstance(ratio, (int, float)) and 0 < float(ratio) < 1:
                return float(ratio)
        return default

    @staticmethod
    def normalize_price(value: Decimal | float | int | str) -> Decimal:
        try:
            return Decimal(value).quantize(Decimal("0.01"))
        except Exception as exc:
            raise AppError(status_code=400, code="invalid_plan_price", message="Invalid plan price") from exc

    def _get_plan_sync(self, plan_id: UUID) -> Plan | None:
        with self._session_factory() as session:
            with session.begin():
                repo = PlanRepository(session)
                return repo.get_by_id(plan_id)

    def _get_plan_by_name_sync(self, name: str) -> Plan | None:
        with self._session_factory() as session:
            with session.begin():
                repo = PlanRepository(session)
                return repo.get_by_name(name)

    def _list_active_sync(self) -> list[Plan]:
        with self._session_factory() as session:
            with session.begin():
                repo = PlanRepository(session)
                return repo.list_active()

