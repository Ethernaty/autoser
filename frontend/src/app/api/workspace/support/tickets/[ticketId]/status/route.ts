import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { patchSupportTicketStatus } from "@/features/workspace/api/server-mvp";
import type { SupportTicketStatus } from "@/features/workspace/types/mvp-types";

export async function PATCH(
  request: NextRequest,
  context: {
    params: { ticketId: string };
  }
) {
  const body = (await request.json().catch(() => ({}))) as {
    status?: SupportTicketStatus;
  };

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "support.update");
    return patchSupportTicketStatus(workspaceContext, context.params.ticketId, body.status ?? "open");
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
