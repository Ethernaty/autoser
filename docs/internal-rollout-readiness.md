# AutoService CRM SaaS - Internal Rollout Readiness

Date: 2026-03-13
Status: Pre-internal rollout assessment (MVP stabilization phase)

## 1) What already works

- Active SaaS backend and frontend MVP paths are implemented and aligned around canonical domain/API naming.
- Canonical UI flow is present:
  - login -> dashboard -> client -> vehicle -> work-order -> lines -> payment -> close.
- Payments are modeled and shown separately from work-order closure.
- Frontend active navigation uses canonical surfaces (`/employees`, `/work-orders`, `total_amount`).
- Legacy pages (`/app/orders`, `/app/new-order`, `/app/today`, `/app/cash-desk`) redirect away from active UX path.
- Workspace settings minimal flow is present (GET/PATCH).
- Workspace switching flow exists via `/auth/workspaces` + `/auth/switch-workspace`.

## 2) What blocks real daily usage

1. Manager role migration may be missing in some environments.
- Symptom: employee creation/update with `role=manager` fails.
- Required: apply migration `backend/alembic/versions/20260313_000004_mvp_domain_alignment.py`.

2. No-go if startup/smoke scripts are stale relative to canonical APIs.
- Fixed in this phase:
  - `backend/scripts/smoke.ps1` now tests canonical MVP runtime.
  - `frontend/scripts/bff_smoke.ps1` now tests canonical BFF endpoints and semantics.

## 3) Risky but tolerable for first internal rollout

- Employee edit is modal-based (no dedicated employee profile screen).
- Work-order selectors are improved with local filtering, but large datasets still need stronger server-driven discoverability later.
- Compatibility aliases (`/users`, `/orders`, `price`, `user_id`) still exist in codebase for transition; active UI does not depend on them.
- Legacy/deferred code remains in repository and can confuse contributors if active docs are not followed.

## 4) Fix-before-daily list (strict)

1. Apply DB migrations to head in each environment.
2. Run backend smoke and frontend BFF smoke successfully.
3. Ensure owner account bootstrap works through API/UI login flow.
4. Validate manager/employee permissions against real operator tasks.
5. Confirm workspace settings are initialized and editable.

## 5) Daily validation scenarios (exact)

### Scenario A - Owner bootstrap (no DB hacking)

1. POST `/auth/register` with new tenant slug.
2. Login via `/login` UI.
3. Verify dashboard opens and workspace context is populated.

Expected:
- Access/refresh cookies are set.
- `/auth/me` resolves valid user/role/workspace.
- No manual DB edits required.

### Scenario B - Client + vehicle creation

1. Create client from `/app/clients`.
2. Create vehicle linked to that client from `/app/vehicles`.
3. Open vehicle detail and confirm linkage.

Expected:
- Vehicle appears in client-linked listings.
- No cross-workspace data leakage.

### Scenario C - Work-order execution

1. Create work-order from `/app/work-orders` with required `vehicle_id`.
2. Add at least one line item.
3. Set status `in_progress` -> `completed`.
4. Close work-order.

Expected:
- `total_amount` is visible and updates correctly.
- Status transition rules are enforced.

### Scenario D - Payment semantics

1. Add payment on work-order detail.
2. Verify `paid_amount` and `remaining_amount` update.
3. Verify payment action is independent from close action.

Expected:
- Remaining amount = max(total_amount - paid_amount, 0).
- Work-order does not auto-close merely due to payment.

### Scenario E - Employee operations

1. Create employee with role `manager`.
2. Toggle active/inactive status.
3. Assign employee to work-order.

Expected:
- Role persists correctly.
- Assignment is reflected in work-order detail/list.

### Scenario F - Workspace settings

1. Open `/app/settings`.
2. Update phone/service fields.

Expected:
- Values persist and reload correctly.

## 6) Operator walkthrough (core flow)

1. Login at `/login`.
2. Open `/app/dashboard` and check open/closed/revenue cards.
3. Create/find client in `/app/clients`.
4. Create/find vehicle in `/app/vehicles` (linked to client).
5. Create work-order in `/app/work-orders` with selected client + vehicle.
6. Open work-order detail and add/edit/remove lines.
7. Assign employee, move statuses.
8. Add payment and verify remaining amount.
9. Close work-order explicitly.

## 7) Environment/setup prerequisites

- Backend:
  - `cd backend`
  - `./scripts/dev_up.ps1`
  - `./scripts/smoke.ps1 -BaseUrl http://127.0.0.1:8000`
- Frontend:
  - `cd frontend`
  - copy `.env.example` -> `.env.local`
  - `npm install`
  - `npm run dev`
  - `./scripts/bff_smoke.ps1 -BackendUrl http://127.0.0.1:8000 -FrontendUrl http://127.0.0.1:3000`

Notes:
- Backend `.env.example` now clearly marks deferred-but-currently-validated variables.
- Frontend `README.md` now reflects active MVP product (not design-system-only state).

## 8) Role assumptions for first internal rollout

- Owner: full operational control, initial bootstrap and settings.
- Admin: full daily operations except owner-only governance constraints.
- Manager: daily workflow management (clients, vehicles, work-orders, payments, employee read).
- Employee: execution support role; verify phone/email masking expectations against real business process.

## 9) Recommended short internal rollout checklist

1. Migrations applied (`alembic upgrade head`) on staging/internal env.
2. Backend smoke script passed.
3. Frontend BFF smoke script passed.
4. Owner bootstrap test passed with fresh tenant.
5. Manager account creation test passed.
6. End-to-end operator flow completed once by owner and once by manager.
7. Capture top friction points daily for first week.

## 10) First-week internal testing checklist (exact)

Day 1:
1. Bootstrap 1 owner + 1 manager + 1 employee.
2. Complete 5 full work-orders end-to-end.
3. Validate payment/remaining correctness on each.

Day 2:
1. Test workspace switching with at least 2 workspaces for one user.
2. Confirm no workspace scope leakage in lists/details.

Day 3:
1. Run status transition stress test (new -> in_progress -> completed -> close) on 20 records.
2. Verify audit entries for critical actions.

Day 4:
1. Validate client/vehicle search behavior with larger datasets.
2. Record selectors/search pain points by role.

Day 5:
1. Replay full smoke scripts.
2. Freeze blocker list for next hardening cycle.

## 11) Go/No-Go recommendation

Decision: **Conditional GO**.

Go criteria for internal daily usage:
- migrations are applied (including manager role migration),
- both smoke scripts pass,
- owner+manager can complete the full operator walkthrough without API or permission failures.

If any criterion fails, decision is **NO-GO** until corrected.
