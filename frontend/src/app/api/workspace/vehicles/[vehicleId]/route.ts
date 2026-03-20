import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { getVehicle, patchVehicle } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function GET(
  request: NextRequest,
  context: {
    params: { vehicleId: string };
  }
) {
  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "vehicles.read");
    return getVehicle(workspaceContext, context.params.vehicleId);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}

export async function PATCH(
  request: NextRequest,
  context: {
    params: { vehicleId: string };
  }
) {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  let payload: {
    plate_number?: string;
    make_model?: string;
    year?: number | null;
    vin?: string | null;
    comment?: string | null;
    archived?: boolean;
  };

  try {
    payload = (await request.json()) as {
      plate_number?: string;
      make_model?: string;
      year?: number | null;
      vin?: string | null;
      comment?: string | null;
      archived?: boolean;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "vehicles.update");
    return patchVehicle(workspaceContext, context.params.vehicleId, payload);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
