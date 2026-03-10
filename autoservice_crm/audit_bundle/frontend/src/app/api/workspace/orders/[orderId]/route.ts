import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import type { OrderStatus } from "@/features/workspace/types";
import { updateOrder } from "@/features/workspace/api/server-workspace";
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
    description?: string;
    price?: number;
    status?: OrderStatus;
  };

  try {
    payload = (await request.json()) as {
      description?: string;
      price?: number;
      status?: OrderStatus;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.description && payload.price === undefined && !payload.status) {
    return NextResponse.json({ message: "No update fields provided" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.edit");

    const updatedOrder = await updateOrder(workspaceContext, orderId, {
      description: payload.description?.trim(),
      price: payload.price,
      status: payload.status
    });

    return updatedOrder;
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}

