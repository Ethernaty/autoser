import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { createOrderFromWorkflow, listOrders } from "@/features/workspace/api/server-workspace";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q") ?? "";
  const limit = Number(request.nextUrl.searchParams.get("limit") ?? "20");
  const offset = Number(request.nextUrl.searchParams.get("offset") ?? "0");

  const result = await runWithWorkspaceSession(request, async (context) =>
    listOrders(context, {
      q: query,
      limit,
      offset
    })
  );

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}

export async function POST(request: NextRequest) {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  const idempotencyKey = request.headers.get("Idempotency-Key") ?? undefined;

  let payload: {
    phone?: string;
    clientName?: string;
    description?: string;
    price?: number;
    selectedClientId?: string;
  };

  try {
    payload = (await request.json()) as {
      phone?: string;
      clientName?: string;
      description?: string;
      price?: number;
      selectedClientId?: string;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (context) => {
    await assertAccess(context, "orders.create");

    const normalizedPayload = {
      phone: payload.phone ?? "",
      clientName: payload.clientName,
      description: payload.description ?? "",
      price: Number(payload.price ?? 0),
      selectedClientId: payload.selectedClientId
    };

    const order = await createOrderFromWorkflow(context, normalizedPayload, { idempotencyKey });

    return order;
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}


