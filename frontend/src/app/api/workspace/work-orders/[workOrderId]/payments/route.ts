import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { createWorkOrderPayment, listWorkOrderPayments } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function GET(
  request: NextRequest,
  context: {
    params: { workOrderId: string };
  }
) {
  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "payments.read");
    return listWorkOrderPayments(workspaceContext, context.params.workOrderId);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}

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

  let payload: {
    amount?: number;
    method?: "cash" | "card" | "transfer" | "other";
    paid_at?: string;
    comment?: string | null;
    external_ref?: string | null;
  };
  try {
    payload = (await request.json()) as {
      amount?: number;
      method?: "cash" | "card" | "transfer" | "other";
      paid_at?: string;
      comment?: string | null;
      external_ref?: string | null;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.amount || !payload.method) {
    return NextResponse.json({ message: "amount and method are required" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "payments.create");
    return createWorkOrderPayment(workspaceContext, context.params.workOrderId, {
      amount: Number(payload.amount),
      method: payload.method!,
      paid_at: payload.paid_at,
      comment: payload.comment ?? null,
      external_ref: payload.external_ref ?? null
    });
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
