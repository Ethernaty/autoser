import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { updateOrderStatus } from "@/features/workspace/api/server-workspace";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function PATCH(
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

  let payload: {
    status?: "new" | "in_progress" | "completed" | "canceled";
  };

  try {
    payload = (await request.json()) as {
      status?: "new" | "in_progress" | "completed" | "canceled";
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.status) {
    return NextResponse.json({ message: "Status is required" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.change_status");

    const updatedOrder = await updateOrderStatus(workspaceContext, orderId, payload.status!);

    return updatedOrder;
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}
