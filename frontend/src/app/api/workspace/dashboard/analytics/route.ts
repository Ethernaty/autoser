import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { getDashboardAnalytics } from "@/features/workspace/api/server-mvp";

export async function GET(request: NextRequest) {
  const months = Number(request.nextUrl.searchParams.get("months") ?? "12");

  const result = await runWithWorkspaceSession(request, async (context) => {
    await assertAccess(context, "orders.read");
    return getDashboardAnalytics(context, months);
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}
