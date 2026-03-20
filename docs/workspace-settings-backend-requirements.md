# Workspace Settings: Backend Requirements for Full Production Support

## Current frontend-safe scope implemented
- Timezone selection now uses a canonical IANA list in frontend and saves `timezone` via existing `PATCH /api/workspace/settings`.
- Address field now supports online autocomplete suggestions and still persists selected text into existing `address` field.
- Logo upload now supports local file selection, preview, replace, and remove in UI only.

## Missing backend requirements

## 1) Logo persistence
Current blocker:
- `WorkspaceSettings` contract has no `logo_url` field.
- No upload endpoint exists in active MVP API.

Required API changes:
- Extend `WorkspaceSettingsResponse` with:
  - `logo_url: string | null`
- Add endpoint:
  - `POST /api/workspace/settings/logo`
  - multipart form-data (`file`)
  - response: updated settings payload or `{ logo_url }`
- Add endpoint:
  - `DELETE /api/workspace/settings/logo`
  - response: updated settings payload or `{ logo_url: null }`

Required storage changes:
- Store logo metadata per workspace:
  - `logo_url`
  - optional `logo_storage_key`
  - optional `logo_updated_at`
- Configure object storage strategy (S3-compatible or local media) and signed/public URL policy.

## 2) Address autocomplete provider hardening
Current frontend behavior:
- Direct client call to provider URL (`NEXT_PUBLIC_ADDRESS_AUTOCOMPLETE_URL`, default Nominatim).

Recommended backend enhancement:
- Add server-side proxy endpoint:
  - `GET /api/workspace/address/suggest?q=...`
- Reason:
  - central provider key/rate-limit control
  - provider swap without frontend changes
  - consistent audit/observability and error handling

Optional persistence enhancement:
- Keep existing `address` string for MVP.
- If needed later, add structured fields:
  - `address_raw`
  - `address_place_id`
  - `address_lat`
  - `address_lng`
  - `address_components_json`

## 3) Validation parity
Recommended backend validation to match frontend behavior:
- `service_name`: non-empty.
- `phone`: non-empty, normalized format policy.
- `timezone`: must be valid IANA timezone.
- `currency`: uppercase ISO currency code whitelist.
