# Backend MVP Runtime Simplification

Date: 2026-03-13  
Entrypoint: `backend/app/main.py`

## Current backend runtime assessment
Before this change, backend runtime always loaded:
- full API surface (MVP + platform/deferred routers),
- presentation/admin runtime,
- deferred middleware layers,
- deferred startup/shutdown components (webhook task registration, job worker, event stream, delivery engine).

This made active MVP request flow hard to identify.

## Middleware before/after
### Before (`app.add_middleware` registration list)
1. `StructuredLoggingMiddleware`
2. `RateLimitMiddleware`
3. `MembershipValidationMiddleware`
4. `AuthMiddleware`
5. `ApiKeyAuthMiddleware`
6. `PresentationAuthMiddleware`
7. `PresentationSecurityMiddleware`

### After (default runtime)
1. `StructuredLoggingMiddleware`
2. `RateLimitMiddleware`
3. `MembershipValidationMiddleware`
4. `AuthMiddleware`

### Conditional (default OFF)
- `ApiKeyAuthMiddleware` only when `ENABLE_DEFERRED_PLATFORM_RUNTIME=true`
- `PresentationAuthMiddleware` and `PresentationSecurityMiddleware` only when `ENABLE_PRESENTATION_RUNTIME=true`

## Router composition before/after
### Before (`main.py` router registration list)
1. `health_router`
2. `auth_router`
3. `audit_router`
4. `api_key_router`
5. `client_router`
6. `employee_router`
7. `order_router`
8. `subscription_router`
9. `webhook_router`
10. `external_api_router`
11. `internal_tenant_router`
12. `presentation_router`
- plus mount: `/admin/static`

### After (default runtime)
1. `health_router`
2. `auth_router`
3. `audit_router`
4. `client_router`
5. `employee_router`
6. `order_router`

### Conditional (default OFF)
- `api_key_router`
- `subscription_router`
- `webhook_router`
- `external_api_router`
- `internal_tenant_router`
- `presentation_router`
- `/admin/static` mount

## Kept runtime modules (active by default)
- Authentication and workspace context: `auth`, JWT auth middleware, membership validation.
- Authorization: permission guard and role matrix checks.
- Core domain APIs: `clients`, `users` (current employees API scope), `orders`.
- Basic audit API: `/audit`.
- Health/stability base: `/health*`, `/metrics`, DB lifecycle, structured logging, error handlers.

## Deferred runtime modules (detached from default app composition)
- Controllers: `api_key`, `subscription`, `webhook`, `external_api`, `internal_tenant`.
- Presentation/admin routes and static admin mount.
- Deferred middleware activation: API-key and presentation security/auth layers.
- Deferred startup/shutdown: webhook task registration, job worker start/stop, queue close, event stream close, HTTP delivery engine close.

## Modules left in codebase but removed from active app composition
- Deferred controllers/services/models/repositories are preserved for future reintroduction.
- Detachment is runtime-flag based; no destructive deletion was performed.

Also removed deferred coupling from active MVP request path:
- `order_controller.py`: removed quota dependencies and payment quota completion hook.
- `employee_controller.py`: removed quota dependency on employee creation.
- `auth_service.py`: removed subscription bootstrap from registration flow.

## Validation and verification results
- Import check: `python -c "import app.main"` -> **passed**.
- Exact active runtime endpoints include: `/health*`, `/auth/*`, `/clients/*`, `/orders/*` -> **active**.
- Deferred endpoints by default:
  - `/subscription/*`, `/webhooks/*`, `/external/*`, `/internal/tenants*`, `/admin/*`, `/app/*` -> **not active**.
- No dead import introduced in default bootstrap path.
- Deferred modules remain coupled only via guarded runtime branches in `main.py` (feature flags), not in default active path.

## Risks and follow-up checks
- Frontend paths still calling deferred subscription endpoints can receive 404 while flags are OFF.
- `.env` values used in existing local/dev setup should be reviewed with new defaults:
  - `ENABLE_DEFERRED_PLATFORM_RUNTIME=false`
  - `ENABLE_PRESENTATION_RUNTIME=false`
- Internal readiness/deps endpoints still include queue/deep checks; keep as-is for now, but verify ops expectations.

## Recommended next backend tasks before frontend completion
1. Complete MVP employee API surface (list/update/delete) aligned with current frontend needs.
2. Implement vehicles domain/API (next planned MVP domain).
3. Add focused API smoke tests for active default runtime profile.
4. Document optional deferred profile startup procedure for future re-enable scenarios.
