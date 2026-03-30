import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { addWorkOrderTimelineComment } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function POST(
  request: NextRequest,
  context: {
    params: { workOrderId: string };
  }
) {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  let payload: { comment?: string };
  try {
    payload = (await request.json()) as { comment?: string };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.comment?.trim()) {
    return NextResponse.json({ message: "comment is required" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.update");
    await addWorkOrderTimelineComment(workspaceContext, context.params.workOrderId, payload.comment!.trim());
    return { ok: true };
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
