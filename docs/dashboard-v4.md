# Dashboard V4 Baseline (Operational + Configurable)

## 1. Server baseline is source of truth
- Baseline is enforced by `DashboardPreferencesService`.
- Canonical baseline includes:
  - required widgets: `kpi_row`, `active_work_orders`
  - canonical widget order
  - allowed variants per widget
  - default density (`compact`)
- `reset_layout` and auto-healing always restore this same baseline behavior.

## 2. `layout_json` strict schema
`layout_json` persists presentation-only configuration:

```json
{
  "version": 1,
  "density": "compact|full",
  "widgets": [
    {
      "id": "kpi_row|active_work_orders|orders_by_month|clients_by_month|revenue_dynamics|weekday_load|client_sources|popular_services",
      "order": 1,
      "visible": true,
      "variant": "allowed-per-widget"
    }
  ]
}
```

Rules:
- unknown widget ids are dropped
- invalid variants are replaced with widget defaults
- required widgets are always visible
- order is normalized to continuous sequence

## 3. `filters_json` vs URL query state
### Persisted user preference (`filters_json`)
- last chosen default `period`
- last chosen default `status_scope`
- last chosen default `assignee_scope`

### URL state (session/navigation state)
- current `mode`
- current `period`
- current `status_scope`
- current `assignee_scope`

URL state is the active view state for current session/deep-link.
`filters_json` defines fallback defaults and reset target.

## 4. Drill-down mapping (widget -> route)
| Widget / KPI | Target route | Query params |
|---|---|---|
| KPI: Open queue | `/app/work-orders` | `status_scope=active` + current `period`, `assignee_scope` |
| KPI: Total orders | `/app/work-orders` | `status_scope=all` + current `period` |
| KPI: Clients total | `/app/clients` | current `period` |
| KPI: Paid 30d | `/app/work-orders` | `payment_scope=paid&period=30d` |
| Active work orders | `/app/work-orders` | current `status_scope` (or active fallback), `period`, `assignee_scope` |
| Orders by month | `/app/work-orders` | `period_month=<period>&status_scope=all` |
| Clients by month | `/app/clients` | `created_month=<period>` |
| Revenue dynamics | `/app/work-orders` | `period_month=<period>&payment_scope=paid` |
| Client sources | `/app/clients` | `source=<source>&period=<current>` |
| Popular services | `/app/work-orders` | `service=<name>&period=180d` |

## 5. Anti-chaos guardrails
- user cannot permanently hide all key widgets
- required widgets are enforced server-side
- invalid layout payloads are normalized (healed)
- reset actions are deterministic (`reset_layout`, `reset_filters`)

## 6. QA checkpoints for V4
### State transition QA
- switching filters does not reflow layout unexpectedly
- loading/empty/error states keep stable block heights
- mode switching keeps click targets stable

### Overlay/pointer QA
- no invisible overlay remains after menu close
- backdrop does not intercept clicks after close
- floating menus keep correct `pointer-events` behavior

## 7. Runtime files
- Backend model: `backend/app/models/dashboard_preference.py`
- Backend service: `backend/app/services/dashboard_preferences_service.py`
- Backend API: `backend/app/controllers/dashboard_controller.py`
- Frontend preferences API route: `frontend/src/app/api/workspace/dashboard/preferences/route.ts`
- Frontend dashboard screen: `frontend/src/features/workspace/ui/dashboard-screen.tsx`
- Work-orders scope query sync: `frontend/src/features/workspace/ui/orders-screen.tsx`
