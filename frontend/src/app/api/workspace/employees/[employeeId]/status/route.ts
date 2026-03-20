import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { patchEmployeeStatus } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

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

  let payload: { is_active?: boolean };
  try {
    payload = (await request.json()) as { is_active?: boolean };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (payload.is_active === undefined) {
    return NextResponse.json({ message: "is_active is required" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "employees.update");
    return patchEmployeeStatus(workspaceContext, context.params.employeeId, payload.is_active!);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
