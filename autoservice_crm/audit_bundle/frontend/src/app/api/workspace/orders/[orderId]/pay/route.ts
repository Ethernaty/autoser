import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { updateOrderStatus } from "@/features/workspace/api/server-workspace";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function POST(
  request: NextRequest,
  context: {
    params: {
      orderId: string;
    };
  }
) {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  const { orderId } = context.params;

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "finance.create_payment");

    const updatedOrder = await updateOrderStatus(workspaceContext, orderId, "completed");

    return updatedOrder;
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}
