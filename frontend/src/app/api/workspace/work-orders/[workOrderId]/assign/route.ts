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

  let payload: { employee_id?: string | null };
  try {
    payload = (await request.json()) as { employee_id?: string | null };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.assign");
    return assignWorkOrder(workspaceContext, context.params.workOrderId, payload.employee_id ?? null);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
