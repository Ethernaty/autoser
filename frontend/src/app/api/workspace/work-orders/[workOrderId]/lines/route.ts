import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { addWorkOrderLine, listWorkOrderLines } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function GET(
  request: NextRequest,
  context: {
    params: { workOrderId: string };
  }
) {
  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.read");
    return listWorkOrderLines(workspaceContext, context.params.workOrderId);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}

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

  if (!payload.line_type || !payload.name || payload.quantity === undefined || payload.unit_price === undefined) {
    return NextResponse.json(
      { message: "line_type, name, quantity and unit_price are required" },
      { status: 400 }
    );
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.update");
    return addWorkOrderLine(workspaceContext, context.params.workOrderId, {
      line_type: payload.line_type!,
      name: payload.name!.trim(),
      quantity: Number(payload.quantity),
      unit_price: Number(payload.unit_price),
      position: payload.position,
      comment: payload.comment ?? null
    });
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
