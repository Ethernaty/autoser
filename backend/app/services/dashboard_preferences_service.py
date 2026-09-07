from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.models.dashboard_preference import DashboardPreference
from app.repositories.dashboard_preference_repository import DashboardPreferenceRepository
from app.services.base_service import BaseService


_BASELINE_VERSION = 1
_DEFAULT_MODE = "operations"
_DEFAULT_DENSITY = "compact"
_DASHBOARD_MODES = {"operations", "analytics"}
_DASHBOARD_DENSITIES = {"compact", "full"}
_STATUS_SCOPES = {
    "all",
    "active",
    "completed",
    "cancelled",
    "completed_unpaid",
    "new",
    "in_progress",
    "completed_paid",
}
_PERIOD_SCOPES = {"3m", "6m", "12m"}
_ASSIGNEE_ALL = "all"
_ASSIGNEE_UNASSIGNED = "unassigned"

_WIDGET_VARIANTS: dict[str, tuple[str, ...]] = {
    "kpi_row": ("default",),
    "active_work_orders": ("queue", "compact"),
    "orders_by_month": ("chart", "table"),
    "clients_by_month": ("chart", "table"),
    "revenue_dynamics": ("chart", "table"),
    "weekday_load": ("compact", "table"),
    "client_sources": ("list", "compact"),
    "popular_services": ("list", "compact"),
}
_MANDATORY_WIDGETS = {"kpi_row", "active_work_orders"}
_WIDGET_ORDER = tuple(_WIDGET_VARIANTS.keys())


def _default_filters_json() -> dict[str, Any]:
    return {
        "version": 1,
        "defaults": {
            "period": "6m",
            "status_scope": "all",
            "assignee_scope": "all",
        },
    }


def _default_layout_json() -> dict[str, Any]:
    widgets: list[dict[str, Any]] = []
    for index, widget_id in enumerate(_WIDGET_ORDER, start=1):
        widgets.append(
            {
                "id": widget_id,
                "order": index,
                "visible": True,
                "variant": _WIDGET_VARIANTS[widget_id][0],
            }
        )
    return {
        "version": 1,
        "density": _DEFAULT_DENSITY,
        "widgets": widgets,
    }


class DashboardPreferencesService(BaseService):
    def __init__(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
        )

    async def get_preferences(self) -> dict[str, Any]:
        self._assert_actor()

        def write_op(db: Session) -> dict[str, Any]:
            repo = DashboardPreferenceRepository(db=db, tenant_id=self.tenant_id)
            current = self._get_or_create_preference_in_tx(db=db, repo=repo)
            normalized = self._normalize_payload(
                mode=current.mode,
                filters_json=current.filters_json,
                layout_json=current.layout_json,
            )

            if (
                current.mode != normalized["mode"]
                or current.filters_json != normalized["filters_json"]
                or current.layout_json != normalized["layout_json"]
                or current.baseline_version != _BASELINE_VERSION
            ):
                current = repo.update(
                    current,
                    mode=normalized["mode"],
                    filters_json=normalized["filters_json"],
                    layout_json=normalized["layout_json"],
                    baseline_version=_BASELINE_VERSION,
                )

            return self._to_response_payload(current)

        return await self.execute_write(write_op, idempotent=False)

    async def update_preferences(
        self,
        *,
        mode: str | None = None,
        filters_json: dict[str, Any] | None = None,
        layout_json: dict[str, Any] | None = None,
        reset_layout: bool = False,
        reset_filters: bool = False,
    ) -> dict[str, Any]:
        self._assert_actor()

        def write_op(db: Session) -> dict[str, Any]:
            repo = DashboardPreferenceRepository(db=db, tenant_id=self.tenant_id)
            current = self._get_or_create_preference_in_tx(db=db, repo=repo)

            effective_mode = mode if mode is not None else current.mode
            effective_filters = _default_filters_json() if reset_filters else (filters_json if filters_json is not None else current.filters_json)
            effective_layout = _default_layout_json() if reset_layout else (layout_json if layout_json is not None else current.layout_json)

            normalized = self._normalize_payload(
                mode=effective_mode,
                filters_json=effective_filters,
                layout_json=effective_layout,
            )

            current = repo.update(
                current,
                mode=normalized["mode"],
                filters_json=normalized["filters_json"],
                layout_json=normalized["layout_json"],
                baseline_version=_BASELINE_VERSION,
            )
            return self._to_response_payload(current)

        return await self.execute_write(write_op, idempotent=False)

    def _get_or_create_preference_in_tx(
        self,
        *,
        db: Session,
        repo: DashboardPreferenceRepository,
    ) -> DashboardPreference:
        self._assert_actor()
        current = repo.get_for_user(user_id=self.actor_user_id)
        if current is not None:
            return current
        return repo.create(
            user_id=self.actor_user_id,
            mode=_DEFAULT_MODE,
            filters_json=_default_filters_json(),
            layout_json=_default_layout_json(),
            baseline_version=_BASELINE_VERSION,
        )

    def _normalize_payload(
        self,
        *,
        mode: str | None,
        filters_json: dict[str, Any] | None,
        layout_json: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "mode": self._normalize_mode(mode),
            "filters_json": self._normalize_filters_json(filters_json),
            "layout_json": self._normalize_layout_json(layout_json),
        }

    @staticmethod
    def _normalize_mode(mode: str | None) -> str:
        candidate = str(mode or _DEFAULT_MODE).strip().lower()
        if candidate not in _DASHBOARD_MODES:
            return _DEFAULT_MODE
        return candidate

    @staticmethod
    def _normalize_filters_json(filters_json: dict[str, Any] | None) -> dict[str, Any]:
        baseline = _default_filters_json()
        raw_defaults = filters_json.get("defaults") if isinstance(filters_json, dict) else None
        if not isinstance(raw_defaults, dict):
            return baseline

        period = str(raw_defaults.get("period") or baseline["defaults"]["period"]).strip().lower()
        if period not in _PERIOD_SCOPES:
            period = baseline["defaults"]["period"]

        status_scope = str(raw_defaults.get("status_scope") or baseline["defaults"]["status_scope"]).strip().lower()
        if status_scope not in _STATUS_SCOPES:
            status_scope = baseline["defaults"]["status_scope"]

        assignee_scope = DashboardPreferencesService._normalize_assignee_scope(raw_defaults.get("assignee_scope"))

        return {
            "version": 1,
            "defaults": {
                "period": period,
                "status_scope": status_scope,
                "assignee_scope": assignee_scope,
            },
        }

    @staticmethod
    def _normalize_layout_json(layout_json: dict[str, Any] | None) -> dict[str, Any]:
        baseline = _default_layout_json()
        raw_widgets = layout_json.get("widgets") if isinstance(layout_json, dict) else None
        raw_density = layout_json.get("density") if isinstance(layout_json, dict) else None

        density = str(raw_density or baseline["density"]).strip().lower()
        if density not in _DASHBOARD_DENSITIES:
            density = baseline["density"]

        baseline_index = {widget_id: index for index, widget_id in enumerate(_WIDGET_ORDER)}
        user_widgets: dict[str, dict[str, Any]] = {}
        if isinstance(raw_widgets, list):
            for raw_item in raw_widgets:
                if not isinstance(raw_item, dict):
                    continue
                widget_id = str(raw_item.get("id") or "").strip()
                if widget_id not in _WIDGET_VARIANTS:
                    continue
                try:
                    order = int(raw_item.get("order"))
                except Exception:
                    order = baseline_index[widget_id] + 1
                visible = bool(raw_item.get("visible", True))
                variant_candidate = str(raw_item.get("variant") or _WIDGET_VARIANTS[widget_id][0]).strip().lower()
                variant = variant_candidate if variant_candidate in _WIDGET_VARIANTS[widget_id] else _WIDGET_VARIANTS[widget_id][0]
                user_widgets[widget_id] = {
                    "id": widget_id,
                    "order": order,
                    "visible": visible,
                    "variant": variant,
                }

        normalized_widgets: list[dict[str, Any]] = []
        for widget_id in _WIDGET_ORDER:
            default_widget = baseline["widgets"][baseline_index[widget_id]]
            candidate = user_widgets.get(widget_id, default_widget)
            normalized_widgets.append(
                {
                    "id": widget_id,
                    "order": candidate["order"],
                    "visible": True if widget_id in _MANDATORY_WIDGETS else bool(candidate["visible"]),
                    "variant": candidate["variant"],
                }
            )

        normalized_widgets.sort(key=lambda item: (int(item["order"]), baseline_index[item["id"]]))
        for position, item in enumerate(normalized_widgets, start=1):
            item["order"] = position

        return {
            "version": 1,
            "density": density,
            "widgets": normalized_widgets,
        }

    @staticmethod
    def _normalize_assignee_scope(raw_scope: object) -> str:
        if raw_scope is None:
            return _ASSIGNEE_ALL
        candidate = str(raw_scope).strip().lower()
        if candidate in {_ASSIGNEE_ALL, _ASSIGNEE_UNASSIGNED}:
            return candidate
        try:
            return str(UUID(str(raw_scope)))
        except Exception:
            return _ASSIGNEE_ALL

    @staticmethod
    def _to_response_payload(current: DashboardPreference) -> dict[str, Any]:
        return {
            "mode": current.mode,
            "filters_json": current.filters_json,
            "layout_json": current.layout_json,
            "baseline_version": current.baseline_version,
        }

    def _assert_actor(self) -> None:
        if self.actor_user_id is None:
            raise AppError(status_code=401, code="actor_required", message="Authenticated actor is required")
