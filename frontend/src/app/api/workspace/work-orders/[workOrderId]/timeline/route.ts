import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { listWorkOrderTimeline } from "@/features/workspace/api/server-mvp";

export async function GET(
  request: NextRequest,
  context: {
    params: { workOrderId: string };
  }
) {
  const limit = Number(request.nextUrl.searchParams.get("limit") ?? "100");
  const offset = Number(request.nextUrl.searchParams.get("offset") ?? "0");

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.read");
    return listWorkOrderTimeline(workspaceContext, context.params.workOrderId, { limit, offset });
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
