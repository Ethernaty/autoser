import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { listVehiclesByClient } from "@/features/workspace/api/server-mvp";

export async function GET(
  request: NextRequest,
  context: {
    params: { clientId: string };
  }
) {
  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "vehicles.read");
    return listVehiclesByClient(workspaceContext, context.params.clientId);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
