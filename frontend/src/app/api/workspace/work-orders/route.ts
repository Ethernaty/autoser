import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { createWorkOrder, listWorkOrders } from "@/features/workspace/api/server-mvp";
import type { DashboardStatusScope } from "@/features/workspace/types/mvp-types";
import { enforceSameOrigin } from "@/shared/security/origin";

const STATUS_SCOPES: DashboardStatusScope[] = [
  "all",
  "active",
  "completed",
  "cancelled",
  "completed_unpaid",
  "new",
  "in_progress",
  "completed_paid"
];

function sanitizeAssigneeScope(raw: string | null): string {
  if (!raw) return "all";
  const value = raw.trim();
  if (!value) return "all";
  if (value === "all" || value === "unassigned") return value;
  if (value.length > 64) return "all";
  if (!/^[a-zA-Z0-9@._:-]+$/.test(value)) return "all";
  return value;
}

function sanitizePositiveInt(raw: string | null, fallback: number, min: number, max: number): number {
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return fallback;
  const normalized = Math.trunc(parsed);
  if (normalized < min) return min;
  if (normalized > max) return max;
  return normalized;
}

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q") ?? "";
  const rawStatusScope = request.nextUrl.searchParams.get("status_scope");
  const statusScope: DashboardStatusScope =
    rawStatusScope && STATUS_SCOPES.includes(rawStatusScope as DashboardStatusScope)
      ? (rawStatusScope as DashboardStatusScope)
      : "all";
  const assigneeScope = sanitizeAssigneeScope(request.nextUrl.searchParams.get("assignee_scope"));
  const limit = sanitizePositiveInt(request.nextUrl.searchParams.get("limit"), 20, 1, 200);
  const offset = sanitizePositiveInt(request.nextUrl.searchParams.get("offset"), 0, 0, 100000);

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.read");
    return listWorkOrders(workspaceContext, { q, status_scope: statusScope, assignee_scope: assigneeScope, limit, offset,
      payment_scope: request.nextUrl.searchParams.get("payment_scope") ?? "all",
      date_from: request.nextUrl.searchParams.get("date_from") ?? undefined,
      date_to: request.nextUrl.searchParams.get("date_to") ?? undefined,
      sort: request.nextUrl.searchParams.get("sort") ?? "updated_desc",
      overdue: request.nextUrl.searchParams.get("overdue") === "true"
    });
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
    mileage?: number | null;
    due_at?: string | null;
    estimated_amount?: number | string | null;
    diagnosis?: string | null;
    intake_notes?: string | null;
    client_id?: string;
    vehicle_id?: string;
    description?: string;
    total_amount?: number;
    assigned_employee_id?: string | null;
    assigned_employee_ids?: string[];
    status?: "new" | "in_progress" | "completed_unpaid" | "completed_paid" | "cancelled";
  };
  try {
    payload = (await request.json()) as {
      mileage?: number | null;
    due_at?: string | null;
    estimated_amount?: number | string | null;
    diagnosis?: string | null;
    intake_notes?: string | null;
    client_id?: string;
      vehicle_id?: string;
      description?: string;
      total_amount?: number;
      assigned_employee_id?: string | null;
      assigned_employee_ids?: string[];
      status?: "new" | "in_progress" | "completed_unpaid" | "completed_paid" | "cancelled";
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.client_id || !payload.vehicle_id || !payload.description) {
    return NextResponse.json(
      { message: "client_id, vehicle_id and description are required" },
      { status: 400 }
    );
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.create");
    return createWorkOrder(
      workspaceContext,
      {
        mileage: payload.mileage,
        due_at: payload.due_at,
        estimated_amount: payload.estimated_amount,
        diagnosis: payload.diagnosis,
        intake_notes: payload.intake_notes,
        client_id: payload.client_id!,
        vehicle_id: payload.vehicle_id!,
        description: payload.description!.trim(),
        total_amount: payload.total_amount !== undefined ? Number(payload.total_amount) : undefined,
        assigned_employee_id: payload.assigned_employee_id ?? null,
        assigned_employee_ids: payload.assigned_employee_ids ?? undefined,
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
