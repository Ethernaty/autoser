import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { attachWorkOrderVehicle } from "@/features/workspace/api/server-mvp";
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

  let payload: { vehicle_id?: string };
  try {
    payload = (await request.json()) as { vehicle_id?: string };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.vehicle_id) {
    return NextResponse.json({ message: "vehicle_id is required" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.update");
    return attachWorkOrderVehicle(workspaceContext, context.params.workOrderId, payload.vehicle_id!);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
