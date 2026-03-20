import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { buildDashboardView } from "@/features/workspace/api/server-workspace";

export async function GET(request: NextRequest) {
  const result = await runWithWorkspaceSession(request, async (context) => buildDashboardView(context));
  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}

