import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { deleteWorkOrderLine, patchWorkOrderLine } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function PATCH(
  request: NextRequest,
  context: {
    params: { workOrderId: string; lineId: string };
  }
) {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  let payload: {
    line_type?: "labor" | "part" | "misc";
    name?: string;
    quantity?: number;
    unit_price?: number;
    position?: number;
    comment?: string | null;
  };
  try {
    payload = (await request.json()) as {
      line_type?: "labor" | "part" | "misc";
      name?: string;
      quantity?: number;
      unit_price?: number;
      position?: number;
      comment?: string | null;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (
    !payload.line_type &&
    !payload.name &&
    payload.quantity === undefined &&
    payload.unit_price === undefined &&
    payload.position === undefined &&
    payload.comment === undefined
  ) {
    return NextResponse.json({ message: "No update fields provided" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.update");
    return patchWorkOrderLine(workspaceContext, context.params.workOrderId, context.params.lineId, payload);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}

export async function DELETE(
  request: NextRequest,
  context: {
    params: { workOrderId: string; lineId: string };
  }
) {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.update");
    await deleteWorkOrderLine(workspaceContext, context.params.workOrderId, context.params.lineId);
    return { ok: true };
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
