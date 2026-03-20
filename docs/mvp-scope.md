# AutoService CRM SaaS MVP Scope

**Document status:** Approved MVP boundary for implementation  
**Date:** 2026-03-13  
**Product direction:** SaaS-only. Desktop development is postponed fully.

## MVP scope statement
MVP is a **single, production-usable SaaS CRM workspace** for an auto service team to run daily operations:
- authenticate into a workspace,
- manage clients and vehicles,
- manage employees and basic roles,
- create and process work orders with basic totals,
- keep a basic audit trail,
- maintain basic service settings.

Everything not required for this day-to-day loop is postponed.

## Included in MVP
1. **Workspace/Tenant foundation**
- Workspace registration and login.
- Workspace switch for users who belong to multiple workspaces.
- Strict tenant isolation in all CRM data operations.

2. **Auth and access**
- Email/password auth with access/refresh session flow.
- Basic roles: `owner`, `admin`, `manager`, `employee`.
- Role-based permissions for clients, vehicles, work orders, employees, settings, and audit read.

3. **Clients**
- Create, list/search, update, soft-delete client records.
- Required fields: name, phone.
- Optional fields: email, comment.

4. **Vehicles** *(missing in SaaS backend today; required for MVP)*
- Create, list/search, update, archive vehicle records.
- Vehicle linked to client.
- Minimal fields: plate number, make/model, year (optional), VIN (optional), comment (optional).

5. **Employees**
- Create employee (existing).
- Add missing endpoints/UI for list, update role/status, remove from workspace.
- Owner protections (cannot remove last owner).

6. **Work orders**
- Create/list/search/update/delete work orders.
- Work order linked to client and vehicle.
- Statuses: `new`, `in_progress`, `completed`, `canceled`.
- Basic fields: description, total amount, assigned employee (optional).

7. **Basic pricing/totals**
- Manual order total input (decimal, validated).
- Totals in UI for filtered order set (sum) and count by status.
- No invoicing ledger, no complex accounting.

8. **Basic service settings**
- Workspace profile settings page: service name, phone, address, timezone, currency.
- Editable by `owner/admin`.

9. **Basic audit trail**
- Write audit records for auth/session events and CRUD/status changes on core entities.
- Read-only audit list page for `owner/admin` with simple filters (date/action/user/entity).

10. **Single web product surface**
- One SaaS web client path for MVP (Next.js app + backend API).
- No parallel product surfaces in MVP release scope.

## Explicitly excluded from MVP for now
1. **Desktop product line**
- `legacy/desktop/main.py`, `legacy/desktop/views/`, and related desktop modules in `legacy/desktop/`.

2. **Billing and monetization stack**
- Plans, subscriptions, billing events, usage quotas, feature-limits as product behavior.
- No paywalls/plan gating in MVP flows.

3. **External platform stack**
- Webhooks, webhook deliveries/retries, integration credentials.
- API keys and public/external API surface.
- Internal admin/service APIs for tenant lifecycle management.

4. **Advanced platform/enterprise modules**
- Advanced observability/monitoring dashboards, tracing pipelines, chaos/failover modules.
- Kafka/job queue/event-stream complexity not required for MVP operations.

5. **Non-essential operational UX**
- Separate operator/admin template UI tracks as product scope.
- Advanced analytics dashboards beyond basic order totals and status counters.
- Advanced finance (refunds, partial payments, payouts, accounting exports).

6. **Scope expansion features**
- Mobile app, partner portal, marketplace integrations, custom workflow engines.

## Core user flows
1. **Owner onboarding**
- Register workspace -> login -> lands in workspace -> can open settings.

2. **Team setup**
- Owner/admin opens Employees -> creates employee -> assigns role -> employee can log in.

3. **Client and vehicle intake**
- Employee/manager creates client -> adds vehicle linked to that client.

4. **Work order creation**
- Employee/manager selects client + vehicle -> enters description + total amount -> saves order in `new`.

5. **Order execution**
- Employee/manager updates status (`new` -> `in_progress` -> `completed` or `canceled`) and edits details if needed.

6. **Operational control**
- Manager/admin filters order list, sees totals/counts, tracks active queue.

7. **Governance**
- Owner/admin reviews audit log for key actions and access events.

## Main business entities required for MVP
1. **Tenant (Workspace)**
- `id`, `name`, `slug`, `state`, timestamps.

2. **WorkspaceSettings**
- `tenant_id`, `service_name`, `phone`, `address`, `timezone`, `currency`, timestamps.

3. **User**
- `id`, `email`, `password_hash`, `is_active`, timestamps.

4. **Membership**
- `user_id`, `tenant_id`, `role`, `version`, timestamps.

5. **Client**
- `id`, `tenant_id`, `name`, `phone`, `email`, `comment`, `deleted_at`, `version`, timestamps.

6. **Vehicle**
- `id`, `tenant_id`, `client_id`, `plate_number`, `make_model`, `year`, `vin`, `comment`, `archived_at`, timestamps.

7. **WorkOrder**
- `id`, `tenant_id`, `client_id`, `vehicle_id`, `assigned_user_id` (nullable), `description`, `total_amount`, `status`, timestamps.

8. **AuditLog**
- `id`, `tenant_id`, `user_id`, `action`, `entity`, `entity_id`, `metadata`, `created_at`.

## Technical modules required for MVP
1. **Backend API modules**
- Keep/finish: `auth`, `clients`, `orders`, `audit`, `employees`.
- Add: `vehicles`, `workspace_settings`.
- Remove from MVP delivery path: `subscription`, `webhook`, `api_key`, `external_api`, `internal_tenant`.

2. **Authorization and tenant guard**
- Enforce tenant scope and role permission checks across all included modules.

3. **Data layer and migrations**
- Add schema for `vehicles` and `workspace_settings`.
- Extend orders with `vehicle_id` and optional `assigned_user_id`.

4. **Frontend modules**
- Required pages: Login, Clients, Vehicles, Work Orders, Employees, Settings, Audit.
- Remove MVP dependency on subscription/plan capability checks.

5. **Audit instrumentation**
- Ensure consistent audit write hooks for all core mutations and auth actions.

6. **Deployment baseline**
- Single backend service + single web frontend + PostgreSQL (+ Redis only if needed for session/rate-limit stability).
- No Kafka/event-stream/webhook worker requirement for MVP launch.

## Risks if scope is not reduced
1. **Launch delay risk**
- Team effort will be spent on billing/webhooks/platform plumbing instead of core CRM readiness.

2. **Quality risk in core operations**
- More moving parts reduce reliability of critical flows (order intake and processing).

3. **Product confusion risk**
- Parallel UI tracks and enterprise surfaces blur what is the actual shipped product.

4. **Operational complexity risk**
- Unneeded infra (queues/events/advanced observability) increases deployment and incident surface.

5. **Maintenance debt risk**
- Supporting non-MVP modules now creates long-term drag before first real customer feedback.

## Final recommended MVP boundary
Ship **only** the SaaS workspace CRM loop:
- `Auth + Workspace + Clients + Vehicles + Employees + Work Orders + Basic Totals + Basic Roles + Basic Audit + Basic Settings`.

Everything else is frozen as **post-MVP backlog** and must not block release.

## Execution summary (next development phase)
1. Freeze non-MVP modules in planning and release criteria.
2. Implement missing MVP gaps first: `vehicles`, `employees management completeness`, `workspace settings`, `order->vehicle link`.
3. Remove subscription/enterprise dependencies from core user flows.
4. Finish end-to-end QA on the 7 core flows above and prepare first production pilot.
