import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { listAuditLogs } from "@/features/audit/api/server-audit";

export async function GET(request: NextRequest) {
  const limit = Number(request.nextUrl.searchParams.get("limit") ?? "25");
  const offset = Number(request.nextUrl.searchParams.get("offset") ?? "0");
  const q = request.nextUrl.searchParams.get("q") ?? undefined;
  const level = request.nextUrl.searchParams.get("level") ?? undefined;

  const result = await runWithWorkspaceSession(request, async (context) =>
    listAuditLogs(context, {
      limit,
      offset,
      q,
      level
    })
  );

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}

