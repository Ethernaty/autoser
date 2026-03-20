import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { buildClientCardView } from "@/features/workspace/api/server-workspace";

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q") ?? "";
  const clientId = request.nextUrl.searchParams.get("clientId") ?? undefined;

  const result = await runWithWorkspaceSession(request, async (context) =>
    buildClientCardView(context, {
      q,
      clientId
    })
  );

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}

