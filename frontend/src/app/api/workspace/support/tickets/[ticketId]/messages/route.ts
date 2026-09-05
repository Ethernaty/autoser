import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { addSupportTicketMessage } from "@/features/workspace/api/server-mvp";

export async function POST(request: NextRequest, context: { params: { ticketId: string } }) {
  const body = (await request.json().catch(() => ({}))) as { message?: string };
  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "support.create");
    return addSupportTicketMessage(workspaceContext, context.params.ticketId, body.message?.trim() ?? "");
  });
  if ("status" in result) return result;
  return withSessionJson(result);
}
