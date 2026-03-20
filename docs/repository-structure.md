# Repository Structure (SaaS Focus Cleanup)

## Why this structure was changed
The repository previously mixed active SaaS code, deferred platform surfaces, and legacy desktop code under one container path, which made the active product boundary unclear.

The structure was cleaned to make SaaS MVP execution obvious and reduce contributor ambiguity.

## Current active structure
Top-level structure:

```text
backend/
frontend/
docs/
scripts/
legacy/
```

Active product start points:
- Backend runtime root: `backend/`
- Frontend runtime root: `frontend/`
- MVP definition: `docs/mvp-scope.md`

## What is considered active
These areas are considered part of the active SaaS MVP delivery path:

- `backend/app/controllers/auth_controller.py`
- `backend/app/controllers/client_controller.py`
- `backend/app/controllers/order_controller.py`
- `backend/app/controllers/audit_controller.py`
- `backend/app/controllers/employee_controller.py` (partial, still to complete within MVP scope)
- `backend/app/models/` for tenant/auth/client/order/audit core
- `backend/app/services/` for auth/client/order/employee/audit core services
- `frontend/src/app/(public)/login`
- `frontend/src/app/(protected)/app/*` SaaS workspace screens
- `frontend/src/app/api/workspace/*`, `frontend/src/app/api/workspaces/*`, `frontend/src/app/auth/*`

## What is considered deferred
Deferred means present in repository but out of active MVP scope.

Backend deferred areas:
- `backend/app/controllers/subscription_controller.py`
- `backend/app/controllers/webhook_controller.py`
- `backend/app/controllers/api_key_controller.py`
- `backend/app/controllers/external_api_controller.py`
- `backend/app/controllers/internal_tenant_controller.py`
- `backend/app/services/subscription_service.py`
- `backend/app/services/plan_service.py`
- `backend/app/services/usage_quota_service.py`
- `backend/app/services/feature_flag_service.py`
- `backend/app/services/webhook_service.py`
- `backend/app/services/api_key_service.py`
- `backend/app/services/integration_service.py`
- `backend/presentation/routes/subscriptions.py`
- `backend/presentation/routes/monitoring.py`
- `backend/presentation/routes/system.py`
- `backend/presentation/routes/tenants.py`
- `backend/presentation/routes/operator_ui.py`

Frontend deferred areas:
- `frontend/src/features/subscription/`
- `frontend/src/app/api/subscription/`

## What is considered legacy
Legacy means intentionally not active for current product direction.

- `legacy/desktop/`
  - Former desktop app modules (`main.py`, `views/`, `services/`, `repositories/`, `models/`, `database/`, desktop db and requirements).
- `legacy/deferred/`
  - Archived bundle artifacts and related deferred files.

## Notes for future contributors
1. Treat this repository as SaaS-first. New product work goes to `backend/` and `frontend/`.
2. Do not expand deferred platform modules unless explicitly planned.
3. Do not revive desktop code in active paths.
4. Before implementation, align with `docs/mvp-scope.md`.
5. Keep active/deferred/legacy boundaries explicit in PR descriptions.
