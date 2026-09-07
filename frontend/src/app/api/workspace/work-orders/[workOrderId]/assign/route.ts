import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { assignWorkOrder } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function POST(
  request: NextRequest,
  context: {
    params: { workOrderId: string };
  }
) {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  let payload: { employee_id?: string | null; employee_ids?: string[] };
  try {
    payload = (await request.json()) as { employee_id?: string | null; employee_ids?: string[] };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  const normalizedEmployeeIds = Array.isArray(payload.employee_ids)
    ? payload.employee_ids.filter((value): value is string => typeof value === "string" && value.length > 0)
    : payload.employee_id
      ? [payload.employee_id]
      : [];

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.assign");
    return assignWorkOrder(workspaceContext, context.params.workOrderId, normalizedEmployeeIds);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
