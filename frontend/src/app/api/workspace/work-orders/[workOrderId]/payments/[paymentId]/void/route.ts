import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { voidWorkOrderPayment } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function POST(request: NextRequest, context: { params: { workOrderId: string; paymentId: string } }) {
  const originError = enforceSameOrigin(request);
  if (originError) return originError;
  const body = (await request.json().catch(() => ({}))) as { reason?: string };
  if (!body.reason?.trim()) return NextResponse.json({ message: "reason is required" }, { status: 400 });
  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "payments.create");
    return voidWorkOrderPayment(workspaceContext, context.params.workOrderId, context.params.paymentId, body.reason!.trim());
  });
  if ("status" in result) return result;
  return withSessionJson(result);
}
