import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { createEmployee, listEmployees } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

function sanitizePositiveInt(value: string | null, fallback: number, min: number, max: number): number {
  const parsed = Number(value ?? String(fallback));
  if (!Number.isFinite(parsed)) return fallback;
  const normalized = Math.trunc(parsed);
  if (normalized < min) return min;
  if (normalized > max) return max;
  return normalized;
}

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q") ?? "";
  const role = request.nextUrl.searchParams.get("role") ?? undefined;
  const limit = sanitizePositiveInt(request.nextUrl.searchParams.get("limit"), 20, 1, 50);
  const offset = sanitizePositiveInt(request.nextUrl.searchParams.get("offset"), 0, 0, 100000);

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "employees.read");
    return listEmployees(workspaceContext, { q, role, limit, offset });
  });

  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}

export async function POST(request: NextRequest) {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  const idempotencyKey = request.headers.get("Idempotency-Key") ?? undefined;

  let payload: {
    full_name?: string;
    email?: string;
    password?: string;
    role?: string;
  };
  try {
    payload = (await request.json()) as {
      full_name?: string;
      email?: string;
      password?: string;
      role?: string;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.full_name || !payload.password || !payload.role) {
    return NextResponse.json({ message: "full_name, password and role are required" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "employees.create");
    return createEmployee(
      workspaceContext,
      { full_name: payload.full_name!, email: payload.email ?? null, password: payload.password!, role: payload.role! },
      { idempotencyKey }
    );
  });

  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
