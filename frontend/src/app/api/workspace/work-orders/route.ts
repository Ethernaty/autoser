import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { createWorkOrder, listWorkOrders } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q") ?? "";
  const limit = Number(request.nextUrl.searchParams.get("limit") ?? "20");
  const offset = Number(request.nextUrl.searchParams.get("offset") ?? "0");

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.read");
    return listWorkOrders(workspaceContext, { q, limit, offset });
  });
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
    client_id?: string;
    vehicle_id?: string;
    description?: string;
    total_amount?: number;
    assigned_employee_id?: string | null;
    status?: "new" | "in_progress" | "completed_unpaid" | "completed_paid" | "cancelled";
  };
  try {
    payload = (await request.json()) as {
      client_id?: string;
      vehicle_id?: string;
      description?: string;
      total_amount?: number;
      assigned_employee_id?: string | null;
      status?: "new" | "in_progress" | "completed_unpaid" | "completed_paid" | "cancelled";
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.client_id || !payload.vehicle_id || !payload.description || !payload.total_amount) {
    return NextResponse.json(
      { message: "client_id, vehicle_id, description and total_amount are required" },
      { status: 400 }
    );
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.create");
    return createWorkOrder(
      workspaceContext,
      {
        client_id: payload.client_id!,
        vehicle_id: payload.vehicle_id!,
        description: payload.description!.trim(),
        total_amount: Number(payload.total_amount),
        assigned_employee_id: payload.assigned_employee_id ?? null,
        status: payload.status ?? "new"
      },
      { idempotencyKey }
    );
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
