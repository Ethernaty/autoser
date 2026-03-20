# AutoService CRM (SaaS-First Repository)

This repository is now focused on the **SaaS AutoService CRM** product only.

## Product status
- Active product direction: **SaaS web CRM**.
- MVP scope is defined in [docs/mvp-scope.md](docs/mvp-scope.md).
- Legacy desktop app is postponed and isolated under `legacy/desktop/`.
- Some platform modules remain in the codebase but are **deferred** and not part of active MVP delivery.

## Repository navigation
- `backend/`  
  SaaS backend (FastAPI). Backend entrypoint: `backend/app/main.py`.
- `frontend/`  
  SaaS web frontend (Next.js). Frontend app source: `frontend/src/`.
- `docs/`  
  Product and engineering documentation.
- `scripts/`  
  Repository-level operational helper scripts.
- `legacy/`  
  Isolated non-active code and artifacts:
  - `legacy/desktop/` (desktop application code)
  - `legacy/deferred/` (archived/deferred artifacts)

See [docs/repository-structure.md](docs/repository-structure.md) for active/deferred/legacy boundaries.

## Where to start
- Backend start point: `cd backend`
- Frontend start point: `cd frontend`
- Scope reference before any feature work: `docs/mvp-scope.md`

## Local MVP quickstart
1. Backend:
   - `cd backend`
   - `.\scripts\dev_up.ps1`
   - backend smoke check: `.\scripts\smoke.ps1 -BaseUrl http://127.0.0.1:8000`
2. Frontend:
   - `cd frontend`
   - copy `.env.example` to `.env.local` and adjust if needed
   - `npm install`
   - `npm run dev`
   - frontend BFF smoke check: `.\scripts\bff_smoke.ps1 -BackendUrl http://127.0.0.1:8000 -FrontendUrl http://127.0.0.1:3000`

## Contributor rule
If a change is not directly required for SaaS MVP operations, treat it as deferred unless explicitly approved.
