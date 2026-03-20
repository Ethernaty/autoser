import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { createEmployee, listEmployees } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q") ?? "";
  const role = request.nextUrl.searchParams.get("role") ?? undefined;
  const limit = Number(request.nextUrl.searchParams.get("limit") ?? "20");
  const offset = Number(request.nextUrl.searchParams.get("offset") ?? "0");

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
    email?: string;
    password?: string;
    role?: string;
  };
  try {
    payload = (await request.json()) as {
      email?: string;
      password?: string;
      role?: string;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.email || !payload.password || !payload.role) {
    return NextResponse.json({ message: "email, password and role are required" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "employees.create");
    return createEmployee(
      workspaceContext,
      { email: payload.email!, password: payload.password!, role: payload.role! },
      { idempotencyKey }
    );
  });

  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
