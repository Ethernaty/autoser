import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { buildCashDeskView } from "@/features/workspace/api/server-workspace";

export async function GET(request: NextRequest) {
  const result = await runWithWorkspaceSession(request, async (context) => buildCashDeskView(context));
  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}

