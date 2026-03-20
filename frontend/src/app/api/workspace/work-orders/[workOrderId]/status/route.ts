import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { setWorkOrderStatus } from "@/features/workspace/api/server-mvp";
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

  let payload: { status?: "new" | "in_progress" | "completed" | "canceled" };
  try {
    payload = (await request.json()) as { status?: "new" | "in_progress" | "completed" | "canceled" };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.status) {
    return NextResponse.json({ message: "status is required" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.change_status");
    return setWorkOrderStatus(workspaceContext, context.params.workOrderId, payload.status!);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
