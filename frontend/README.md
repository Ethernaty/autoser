# AutoService CRM SaaS Frontend

Active MVP frontend (Next.js App Router) for daily auto-service operations.

## Prerequisites

- Node.js 20+
- Running backend API (default `http://127.0.0.1:8001`)

## Environment

Create `frontend/.env.local`:

```env
BACKEND_API_URL=http://127.0.0.1:8001
NEXT_PUBLIC_API_BASE_URL=
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
NEXT_PUBLIC_APP_NAME=AutoService SaaS
```

Notes:
- `BACKEND_API_URL` is used by server routes (BFF).
- `NEXT_PUBLIC_API_BASE_URL` should stay empty for same-origin BFF calls.

## Run

```bash
npm install
npm run dev
```

## Validation

```bash
npm run typecheck
npm run lint
npm run build
```

## Active MVP screens

- `/login`
- `/app/dashboard`
- `/app/clients`
- `/app/vehicles`
- `/app/employees`
- `/app/work-orders`
- `/app/settings`

Legacy paths like `/app/orders` and `/app/new-order` redirect to canonical routes.
