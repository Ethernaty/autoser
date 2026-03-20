import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { getEmployee, patchEmployee } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function GET(
  request: NextRequest,
  context: {
    params: { employeeId: string };
  }
) {
  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "employees.read");
    return getEmployee(workspaceContext, context.params.employeeId);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}

export async function PATCH(
  request: NextRequest,
  context: {
    params: { employeeId: string };
  }
) {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  let payload: {
    email?: string;
    password?: string;
    role?: string;
    is_active?: boolean;
  };
  try {
    payload = (await request.json()) as {
      email?: string;
      password?: string;
      role?: string;
      is_active?: boolean;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "employees.update");
    return patchEmployee(workspaceContext, context.params.employeeId, payload);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
