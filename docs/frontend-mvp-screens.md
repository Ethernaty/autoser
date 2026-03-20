# AutoService CRM SaaS Frontend MVP Screens

Date: 2026-03-13  
Status: Active MVP frontend implementation (canonical API-first)

## Completed screens

1. Auth
- Login page is active.
- Session bootstrap is active (`/auth/me` via frontend auth route).
- Protected routing is active.
- Logout action is active.
- Unauthorized handling remains active through API client interceptor and auth bootstrap.

2. Dashboard
- Screen: `/app/dashboard`
- Uses canonical summary endpoint.
- Includes KPI cards and recent activity list.
- Includes quick navigation to clients, vehicles, work-orders.

3. Clients
- Screen: `/app/clients`
- Features: list, search, create, update modal, open detail.
- Detail screen: `/app/clients/{clientId}`
- Features: client profile update and vehicle list by client.

4. Vehicles
- Screen: `/app/vehicles`
- Features: list, search, create, update, open detail.
- Detail screen: `/app/vehicles/{vehicleId}`
- Features: vehicle edit + linked work-order history.

5. Employees
- Screen: `/app/employees`
- Features: list, search, create, update, activate/deactivate.
- Uses canonical `/employees` contracts.

6. WorkOrders
- Screen: `/app/work-orders`
- Features: list, search, create with required `vehicle_id`, status actions, assign action, close action, open detail.
- Detail screen: `/app/work-orders/{workOrderId}`
- Features:
  - status transitions
  - close work-order action
  - attach vehicle
  - assign/unassign employee
  - order lines list/add/edit/remove
  - totals and remaining display via `total_amount` semantics
  - payments list and add-payment flow

7. Payments
- Implemented inside work-order detail as a dedicated block.
- Payment actions are independent from close/status actions in UI and API usage.

8. Workspace settings
- Screen: `/app/settings`
- Minimal MVP settings GET/PATCH flow implemented.

## Partially completed screens

1. Employee detail
- Dedicated employee detail page is not separate; edit is modal-driven in list screen.
- Functional for MVP operations.

2. Work-order detail selector UX
- Vehicle/employee pickers are usable and searchable, but large workspaces still need stronger discoverability (e.g. async server-side search).
- Functional for MVP operations.

## Pending screens

1. None required for strict MVP flow.

## Backend dependencies still missing or sensitive

1. Backend permission matrix behavior depends on role grants.
- Frontend assumes canonical permissions are enforced server-side.

2. If backend temporary aliases are removed, legacy frontend files still present in repository (not active path) may fail if used directly.

## Canonical endpoint usage map per screen

1. Login/Auth bootstrap
- `/auth/login`
- `/auth/me`
- `/auth/logout`
- `/auth/refresh`

2. Dashboard (`/app/dashboard`)
- `GET /api/workspace/dashboard/summary` -> backend `GET /dashboard/summary`

3. Clients (`/app/clients`, `/app/clients/{clientId}`)
- `GET /api/workspace/clients`
- `POST /api/workspace/clients`
- `GET /api/workspace/clients/{clientId}`
- `PATCH /api/workspace/clients/{clientId}`
- `GET /api/workspace/vehicles/by-client/{clientId}`

4. Vehicles (`/app/vehicles`, `/app/vehicles/{vehicleId}`)
- `GET /api/workspace/vehicles`
- `POST /api/workspace/vehicles`
- `GET /api/workspace/vehicles/{vehicleId}`
- `PATCH /api/workspace/vehicles/{vehicleId}`
- `GET /api/workspace/vehicles/{vehicleId}/work-orders`

5. Employees (`/app/employees`)
- `GET /api/workspace/employees`
- `POST /api/workspace/employees`
- `PATCH /api/workspace/employees/{employeeId}`
- `PATCH /api/workspace/employees/{employeeId}/status`

6. WorkOrders (`/app/work-orders`, `/app/work-orders/{workOrderId}`)
- `GET /api/workspace/work-orders`
- `POST /api/workspace/work-orders`
- `GET /api/workspace/work-orders/{workOrderId}`
- `PATCH /api/workspace/work-orders/{workOrderId}`
- `POST /api/workspace/work-orders/{workOrderId}/status`
- `POST /api/workspace/work-orders/{workOrderId}/assign`
- `POST /api/workspace/work-orders/{workOrderId}/attach-vehicle`
- `POST /api/workspace/work-orders/{workOrderId}/close`
- `GET /api/workspace/work-orders/{workOrderId}/lines`
- `POST /api/workspace/work-orders/{workOrderId}/lines`
- `PATCH /api/workspace/work-orders/{workOrderId}/lines/{lineId}`
- `DELETE /api/workspace/work-orders/{workOrderId}/lines/{lineId}`
- `GET /api/workspace/work-orders/{workOrderId}/payments`
- `POST /api/workspace/work-orders/{workOrderId}/payments`

7. Workspace settings (`/app/settings`)
- `GET /api/workspace/context`
- `GET /api/workspace/settings`
- `PATCH /api/workspace/settings`

## Legacy compatibility still temporarily used

1. Backend alias fields may still exist (`price`, `user_id`), but active MVP UI uses canonical fields (`total_amount`, `employee_id`) as primary naming.
2. Legacy frontend pages and BFF routes (`/app/orders`, `/api/workspace/orders`, `/api/workspace/users`) remain in repository for compatibility, but active navigation and active MVP screens use canonical paths.

## Top UX risks / rough edges

1. Order-line editing uses prompt-based editing (functional but not polished).
2. Work-order assignment in list view is minimal and defaults to quick assign action.
3. Vehicle and employee pickers can become long without advanced filtering.
4. Numeric field validation messages are minimal and not fully localized.
5. Legacy code still exists in repository and may cause contributor confusion if active-path docs are ignored.
