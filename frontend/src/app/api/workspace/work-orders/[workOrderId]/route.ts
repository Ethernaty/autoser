import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { getWorkOrder, patchWorkOrder } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function GET(
  request: NextRequest,
  context: {
    params: { workOrderId: string };
  }
) {
  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.read");
    return getWorkOrder(workspaceContext, context.params.workOrderId);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}

export async function PATCH(
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
    description?: string;
    total_amount?: number;
    status?: "new" | "in_progress" | "completed" | "canceled";
    vehicle_id?: string;
    assigned_employee_id?: string | null;
  };
  try {
    payload = (await request.json()) as {
      description?: string;
      total_amount?: number;
      status?: "new" | "in_progress" | "completed" | "canceled";
      vehicle_id?: string;
      assigned_employee_id?: string | null;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (
    !payload.description &&
    payload.total_amount === undefined &&
    !payload.status &&
    !payload.vehicle_id &&
    payload.assigned_employee_id === undefined
  ) {
    return NextResponse.json({ message: "No update fields provided" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.update");
    return patchWorkOrder(workspaceContext, context.params.workOrderId, payload);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
