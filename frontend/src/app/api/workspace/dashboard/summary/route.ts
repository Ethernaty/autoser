import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { getDashboardSummary } from "@/features/workspace/api/server-mvp";

export async function GET(request: NextRequest) {
  const recentLimit = Number(request.nextUrl.searchParams.get("recent_limit") ?? "10");

  const result = await runWithWorkspaceSession(request, async (context) => {
    await assertAccess(context, "orders.read");
    return getDashboardSummary(context, recentLimit);
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}
