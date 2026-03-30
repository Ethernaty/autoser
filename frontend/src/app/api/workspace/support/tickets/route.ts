import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { createSupportTicket, listSupportTickets } from "@/features/workspace/api/server-mvp";
import type { SupportTicketCategory, SupportTicketStatus } from "@/features/workspace/types/mvp-types";

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q") ?? "";
  const statusRaw = request.nextUrl.searchParams.get("status");
  const categoryRaw = request.nextUrl.searchParams.get("category");
  const myOnly = request.nextUrl.searchParams.get("my_only") === "true";
  const limit = Number(request.nextUrl.searchParams.get("limit") ?? "20");
  const offset = Number(request.nextUrl.searchParams.get("offset") ?? "0");

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "support.read");
    return listSupportTickets(workspaceContext, {
      q: q || undefined,
      status: (statusRaw as SupportTicketStatus | null) ?? undefined,
      category: (categoryRaw as SupportTicketCategory | null) ?? undefined,
      my_only: myOnly,
      limit,
      offset
    });
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}

export async function POST(request: NextRequest) {
  const body = (await request.json().catch(() => ({}))) as {
    subject?: string;
    category?: SupportTicketCategory;
    message?: string;
  };

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "support.create");
    return createSupportTicket(workspaceContext, {
      subject: body.subject?.trim() ?? "",
      category: body.category ?? "general",
      message: body.message?.trim() ?? ""
    });
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
