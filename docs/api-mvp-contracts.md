# AutoService CRM SaaS MVP API Contracts

Date: 2026-03-13  
Status: Active MVP API contract (post domain alignment)

## Scope
This contract covers only active MVP backend surface:
- Auth/session
- Workspace context/settings
- Clients
- Vehicles
- Employees
- Work Orders (including lines and payments)
- Dashboard summary
- Audit

Deferred platform APIs (subscription, billing platform, api keys, webhook, external/internal platform) are out of this contract.

## Common auth and scope rules
- Authentication: `Authorization: Bearer <access_token>`
- Workspace scope: inferred from token membership context (`tenant_id` in backend internals).
- Idempotency: optional `Idempotency-Key` supported on selected create endpoints.
- Permission checks: role-based guard per endpoint (`owner`, `admin`, `manager`, `employee`).

## Common error shape
All API errors use:

```json
{
  "error": {
    "code": "string_code",
    "message": "human readable message",
    "details": {}
  }
}
```

Common codes:
- `validation_error`
- `permission_denied`
- `tenant_mismatch`
- `work_order_not_found`
- `vehicle_not_found`
- `order_line_not_found`
- `payment_exceeds_remaining`
- `invalid_status_transition`
- `empty_update`

## Endpoint map

### 1. Auth
- `POST /auth/login` -> login with email/password (+ optional workspace slug)
- `POST /auth/refresh` -> refresh access/refresh pair
- `POST /auth/logout` -> revoke refresh token
- `GET /auth/me` -> current user + current workspace + role
- `GET /auth/workspaces` -> available workspaces for user
- `POST /auth/switch-workspace` -> switch active workspace token context

### 2. Workspace context/settings
- `GET /workspace/context`
  - Response: `workspace_id`, `workspace_slug`, `workspace_name`, `role`, `user_id`
  - Auth: authenticated user
- `GET /workspace/settings`
  - Response: minimal service settings (`service_name`, `phone`, `address`, `timezone`, `currency`, `working_hours_note`)
  - Auth: `workspace_settings:read`
- `PATCH /workspace/settings`
  - Request: partial update of basic service settings
  - Response: updated settings
  - Auth: `workspace_settings:manage`

### 3. Clients
- `GET /clients` -> paginated list/search
- `GET /clients/{client_id}` -> detail
- `POST /clients` -> create
- `PATCH /clients/{client_id}` -> update
- `DELETE /clients/{client_id}` -> soft-delete
- `POST /clients/batch` -> fetch by IDs

### 4. Vehicles
- `GET /vehicles` -> paginated list/search (optional `client_id`)
- `GET /vehicles/{vehicle_id}` -> detail
- `POST /vehicles` -> create
- `PATCH /vehicles/{vehicle_id}` -> update/archive
- `GET /vehicles/by-client/{client_id}` -> list by client
- `GET /vehicles/{vehicle_id}/work-orders` -> vehicle-linked work order history

### 5. Employees
- `GET /employees` -> paginated list/search/filter by role
- `GET /employees/{employee_id}` -> detail
- `POST /employees` -> create/invite/bootstrap
- `PATCH /employees/{employee_id}` -> update email/password/role/is_active
- `PATCH /employees/{employee_id}/status` -> activate/deactivate
- `DELETE /employees/{employee_id}` -> remove membership

### 6. Work Orders
- `GET /work-orders` -> paginated list/search
- `GET /work-orders/{work_order_id}` -> detail
- `POST /work-orders` -> create (requires `client_id`, `vehicle_id`, `description`, `total_amount`)
- `PATCH /work-orders/{work_order_id}` -> update
- `POST /work-orders/{work_order_id}/status` -> explicit status transition
- `POST /work-orders/{work_order_id}/assign` -> assign/unassign employee
- `POST /work-orders/{work_order_id}/attach-vehicle` -> reattach vehicle
- `POST /work-orders/{work_order_id}/close` -> close as completed

Order lines:
- `GET /work-orders/{work_order_id}/lines`
- `POST /work-orders/{work_order_id}/lines`
- `PATCH /work-orders/{work_order_id}/lines/{line_id}`
- `DELETE /work-orders/{work_order_id}/lines/{line_id}`

Totals semantics:
- `total_amount` is canonical monetary field.
- Order line mutations trigger total recalculation.

### 7. Payments
- `GET /work-orders/{work_order_id}/payments` -> list payments for work order
- `POST /work-orders/{work_order_id}/payments` -> create payment for work order

Payment semantics:
- Payments are first-class records.
- Payment does not auto-close work order.
- Overpayment is rejected using `payment_exceeds_remaining`.

### 8. Dashboard
- `GET /dashboard/summary`
  - Response includes:
    - `open_work_orders_count`
    - `closed_work_orders_count`
    - `revenue_total`
    - `recent_activity[]`

### 9. Audit
- `GET /audit` -> paginated audit list (admin/owner gate)
- `POST /audit/events` -> internal service audit append (internal auth dependency)

## DTO contract highlights

### Work order create/update transitional fields
- Canonical request field: `total_amount`
- Transitional accepted request field: `price` (mapped to `total_amount`)
- Canonical assignment field: `assigned_employee_id`
- Transitional accepted field: `assigned_user_id`

### Work order response
Response contains both:
- `total_amount` (canonical)
- `price` (temporary compatibility mirror of `total_amount`)

### Employee response
Response contains both:
- `employee_id` (canonical)
- `user_id` (temporary compatibility mirror)

## Transitional compatibility layers
Temporary compatibility kept to reduce cutover risk:
1. Legacy employees path kept:
- `POST/GET/PATCH/DELETE /users/*` as aliases of `/employees/*` (hidden from API schema).

2. Legacy orders path kept:
- `POST/GET/PATCH /orders/*` as aliases of `/work-orders/*` for base CRUD.

3. Monetary field alias:
- `price` accepted in work-order create/update request.
- `price` still present in work-order response as mirror field.

These compatibility layers are temporary and should be removed after frontend/BFF migration to canonical fields/routes.

## Tenant/workspace vocabulary note
- Storage/runtime internals remain `tenant_*`.
- Public context endpoint and frontend-facing control endpoints use `workspace` naming.
- Business entity payloads still include `tenant_id` during transition to avoid breaking existing consumers.
