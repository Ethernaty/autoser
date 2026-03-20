import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { closeWorkOrder } from "@/features/workspace/api/server-mvp";
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

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.close");
    return closeWorkOrder(workspaceContext, context.params.workOrderId);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
