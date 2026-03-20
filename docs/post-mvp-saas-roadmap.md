# Post-MVP SaaS Roadmap (After Internal Stabilization)

Date: 2026-03-13
Scope: strict post-MVP sequencing for deferred platform capabilities without destabilizing active internal operations.

## Decision baseline

- Current status is **Conditional GO** for internal daily usage.
- Core MVP value is already delivered on canonical contracts (`/employees`, `/work-orders`, `total_amount`, payments separate from closure).
- Deferred/platform runtime remains disabled by default:
  - `ENABLE_DEFERRED_PLATFORM_RUNTIME=false`
  - `ENABLE_PRESENTATION_RUNTIME=false`
- Priority now is stability, not platform breadth.

## Deferred module assessment

### 1) Subscription / Plan / Usage Quotas
- Module name: Subscription/plan/quota stack (`subscription_controller`, `subscription_service`, `plan_service`, `usage_quota_service`, frontend `features/subscription`, frontend `/api/subscription`)
- Current code status: Present in backend and frontend; partially detached from core flow; still references plan/usage abstractions.
- Current runtime status: OFF in backend runtime by default; frontend route exists but not used in active navigation.
- Business value: Low for immediate internal stage; no confirmed external monetization requirement.
- Implementation complexity: High (policy, migration, UX, role/process implications).
- Operational risk: High (can break operator workflows via quotas/plan gating).
- Should be restored: **Needed later**.
- Recommended sequencing: Stage 3 (after stable multi-user internal adoption and monetization/integration trigger).
- Prerequisites:
  - explicit billing or quota business decision,
  - plan catalog ownership,
  - UX policy for quota failures,
  - migration/test coverage for quota side effects.

### 2) API Keys
- Module name: API key management and auth (`api_key_controller`, `api_key_service`, `api_key_auth_middleware`, scope guard)
- Current code status: Present; not part of active MVP flow.
- Current runtime status: OFF unless deferred runtime flag is enabled.
- Business value: Medium only when a real external integration consumer exists.
- Implementation complexity: Medium-High (security lifecycle, scope model, rotation/revocation operations).
- Operational risk: High (new external attack surface).
- Should be restored: **Needed later**.
- Recommended sequencing: Stage 2, only together with a concrete integration use case.
- Prerequisites:
  - defined integration consumer,
  - scope matrix review against canonical work-order model,
  - key management runbook and audit policy.

### 3) Webhooks
- Module name: Webhook endpoints/events/deliveries + worker/event stream/http delivery (`webhook_controller`, `webhook_service`, webhook tasks)
- Current code status: Present; includes async delivery and retry pipeline.
- Current runtime status: OFF unless deferred runtime flag is enabled.
- Business value: Low without active outbound integrations/customers.
- Implementation complexity: High (delivery semantics, retries, dead letters, observability).
- Operational risk: High (queue/worker/HTTP delivery complexity).
- Should be restored: **Needed later**.
- Recommended sequencing: Stage 2, after API integration demand is validated.
- Prerequisites:
  - at least one real webhook consumer,
  - signing/verification policy,
  - on-call playbook for retries/failures.

### 4) External API (public integration surface)
- Module name: External API v1 (`external_api_controller`)
- Current code status: Present but tied to legacy order semantics (`/orders`, `price`) instead of canonical work-order contracts.
- Current runtime status: OFF unless deferred runtime flag is enabled.
- Business value: Low for current internal stage.
- Implementation complexity: High (requires canonical contract rewrite before safe exposure).
- Operational risk: High (public contract drift + security burden).
- Should be restored: **Needed later** (as rewrite, not simple re-enable).
- Recommended sequencing: Stage 2 after internal stability and integration demand.
- Prerequisites:
  - canonical external contract spec based on `/work-orders`,
  - API versioning strategy,
  - auth/rate-limit and support policy.

### 5) Internal tenant/admin routes
- Module name: Internal tenant operations (`internal_tenant_controller`)
- Current code status: Present; currently coupled to subscription status/plan operations.
- Current runtime status: OFF unless deferred runtime flag is enabled.
- Business value: Medium for support operations once internal usage expands across multiple workspaces.
- Implementation complexity: Medium (decouple mandatory subscription coupling first).
- Operational risk: Medium-High (tenant state controls are high impact).
- Should be restored: **Needed next** (limited scope only).
- Recommended sequencing: Stage 1, but only as minimal internal-only ops subset.
- Prerequisites:
  - decouple suspend/resume from mandatory billing operations,
  - strict internal auth and audit trail,
  - explicit runbook and approval policy.

### 6) Monitoring/System/Operator UI routes (presentation)
- Module name: Presentation admin/operator server-rendered routes (`presentation/routes/*` including `monitoring.py`, `system.py`, `operator_ui.py`, `subscriptions.py`, `tenants.py`, `crm_app.py`)
- Current code status: Present legacy SSR surface overlapping with Next.js frontend.
- Current runtime status: OFF unless presentation runtime flag is enabled.
- Business value: Low/negative (duplicate UI stack, contributor confusion).
- Implementation complexity: Medium to keep secure and coherent.
- Operational risk: Medium (parallel UI paths and inconsistent behavior).
- Should be restored: **Not needed**.
- Recommended sequencing: Keep OFF; schedule removal after verification window.
- Prerequisites (for removal):
  - confirm no active internal users depend on `/admin`/`/app` presentation pages,
  - snapshot/archive templates if needed.

### 7) Presentation auth/security middleware and static mount
- Module name: Presentation middleware (`presentation/middleware.py`, `presentation/security_middleware.py`, `/admin/static` mount)
- Current code status: Present but only relevant to presentation routes.
- Current runtime status: OFF unless presentation runtime flag is enabled.
- Business value: Low when presentation routes are not part of product direction.
- Implementation complexity: Low to leave disabled; Medium to maintain if revived.
- Operational risk: Medium if revived (extra auth/session/CSRF path).
- Should be restored: **Not needed**.
- Recommended sequencing: Keep OFF; remove with presentation route cleanup.
- Prerequisites: same as presentation route removal.

### 8) Advanced audit tooling
- Module name: Non-MVP audit expansion (admin monitoring views, richer audit analytics)
- Current code status: Base audit API is active; advanced monitoring/audit-adjacent admin tools exist in presentation layer.
- Current runtime status: Base audit ON; advanced presentation tooling OFF.
- Business value: High for accountability once more internal users operate daily.
- Implementation complexity: Medium (prefer API-level enhancement, not presentation revival).
- Operational risk: Low-Medium.
- Should be restored: **Needed next** (API-first, no presentation reactivation).
- Recommended sequencing: Stage 1 after first week usage feedback.
- Prerequisites:
  - define operator/admin audit questions (who changed what/when),
  - add export/filter requirements,
  - keep role gating strict (owner/admin).

### 9) Tracing / advanced observability
- Module name: Tracing and deeper telemetry (`core/tracing.py`, metrics infrastructure, internal `/metrics`/`/health/deps`)
- Current code status: Metrics and health endpoints active; tracing module exists but not wired into bootstrap path.
- Current runtime status: Partial ON (metrics/health), tracing effectively OFF.
- Business value: High for early incident triage after internal launch.
- Implementation complexity: Medium.
- Operational risk: Low-Medium (if introduced behind flags and internal endpoints).
- Should be restored: **Needed next** (minimal, controlled activation).
- Recommended sequencing: Stage 1, first capability to reintroduce.
- Prerequisites:
  - define telemetry sink (console/OTLP) and retention,
  - wire init/shutdown safely,
  - avoid enabling deferred platform runtime bundle.

### 10) Frontend deferred subscription/platform code
- Module name: Frontend subscription feature package + BFF subscription route (`frontend/src/features/subscription`, `frontend/src/app/api/subscription`)
- Current code status: Present, not used in active MVP navigation; adds conceptual noise.
- Current runtime status: Inactive from UX standpoint, but code path exists.
- Business value: Low in immediate post-MVP internal stage.
- Implementation complexity: Medium to keep in sync with backend deferred modules.
- Operational risk: Medium (reintroduces plan-based mental model prematurely).
- Should be restored: **Not needed** now.
- Recommended sequencing: Keep disabled; candidate for archive/removal if unused after internal stabilization window.
- Prerequisites (for removal):
  - confirm no screen imports this module in active path,
  - document deletion in migration note.

### 11) Legacy compatibility layers (alias surfaces)
- Module name: Legacy endpoint/name compatibility (`/orders`, `/users`, legacy frontend BFF/routes/hooks)
- Current code status: Present for backward compatibility; not canonical path.
- Current runtime status: Partly active (backend legacy routers are included; frontend legacy pages route/redirect).
- Business value: Short-term transition only.
- Implementation complexity: Low to remove once consumers migrated.
- Operational risk: Medium if kept too long (ambiguity and duplicate semantics).
- Should be restored: **Not needed** (already only compatibility).
- Recommended sequencing: schedule deletion, not reactivation.
- Prerequisites:
  - verify no active clients/UI calls to legacy aliases,
  - announce cutoff date,
  - remove with regression check.

## Classification summary

## Needed next
1. Tracing / advanced observability (minimal controlled activation, no deferred bundle enable).
2. Advanced audit tooling (API-first enhancement, no presentation UI revival).
3. Internal tenant/admin operations (limited internal subset, decoupled from subscription).

## Needed later
1. API keys.
2. External API (rewrite to canonical work-order contracts first).
3. Webhooks and async delivery pipeline.
4. Subscription/plan/usage quota stack.

## Not needed
1. Presentation monitoring/system/operator/subscription/tenant/crm SSR routes.
2. Presentation auth/security middleware path.
3. Frontend deferred subscription/platform package for current phase.
4. Legacy compatibility layers (`/orders`, `/users`, old BFF/workspace-api hooks) as permanent surfaces.

## Strict staged reintroduction roadmap

### Stage 0 (Now -> first week internal usage)
- Keep both deferred runtime flags OFF.
- Run current MVP smoke checks daily.
- Collect real pain points and incident classes.

### Stage 1 (Immediately after 1 week internal usage)
1. Reintroduce minimal tracing/observability (internal-only telemetry path, no presentation runtime).
2. Extend audit capability for operator/admin diagnostics (API-first).
3. Reintroduce a **minimal** internal tenant ops subset (if support pressure appears), without full subscription coupling.

### Stage 2 (Only after stable multi-user internal adoption)
4. Reintroduce API keys + external API together, but only on canonical contracts and real integration demand.
5. Reintroduce webhooks only for a confirmed integration consumer.

### Stage 3 (Monetization/commercial trigger only)
6. Reintroduce subscription/plan/usage quota stack.

### Parallel cleanup track (do not postpone indefinitely)
- Remove/deprecate presentation SSR route stack.
- Remove frontend deferred subscription module if unused after stabilization window.
- Remove legacy compatibility aliases after call-site verification.

## Safest order of reactivation

1. Tracing/observability (lowest product-surface risk, highest operational diagnostic value).
2. Advanced audit tooling (internal accountability value, low external risk).
3. Minimal internal tenant ops (support-only, strict auth).
4. API keys + external API (security and contract hardening needed first).
5. Webhooks (after external API and integration contract maturity).
6. Subscription/plan/usage quotas (last, when business model requires it).

## Why specific modules stay postponed

- Subscription/quota now would add policy complexity without immediate internal value.
- Webhooks without live integrations add runtime burden with no user value.
- API keys before integration demand only increases attack surface.
- Presentation admin/operator routes duplicate the active Next.js product and increase confusion.

## Removal candidates (prefer deletion over restoration)

1. `backend/presentation/routes/*` (server-rendered admin/operator UI stack) after verification window.
2. `frontend/src/features/subscription/*` and `frontend/src/app/api/subscription/route.ts` if not used after stabilization period.
3. Legacy compatibility surfaces:
   - backend legacy routers (`/orders`, `/users` aliases),
   - frontend legacy BFF/routes/hooks (`/api/workspace/orders`, `/api/workspace/users`, old `workspace-api` stack).

## Verification notes

- Subscription/plan logic near-term value for internal use: **Low**.
- Webhooks immediate value without active integrations/customers: **No**.
- API keys should remain disabled until external integration need: **Yes**.
- Monitoring/system/operator UI routes worth reviving now: **No** (keep OFF).
- Tracing/advanced observability before broader rollout: **Yes, minimal activation is justified**.
- Deferred frontend subscription/platform code: **Prefer removal/archival unless explicit near-term reactivation plan exists**.
- Legacy compatibility code: **Schedule deletion after usage verification, do not preserve as long-term architecture**.
