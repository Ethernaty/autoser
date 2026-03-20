import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { getWorkspaceContext } from "@/features/workspace/api/server-mvp";

export async function GET(request: NextRequest) {
  const result = await runWithWorkspaceSession(request, async (context) => {
    return getWorkspaceContext(context);
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}
