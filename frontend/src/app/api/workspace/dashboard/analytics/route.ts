import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { getDashboardAnalytics } from "@/features/workspace/api/server-mvp";
import type { DashboardStatusScope } from "@/features/workspace/types/mvp-types";

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

function sanitizeMonths(raw: string | null): number {
  const parsed = Number(raw ?? "12");
  if (!Number.isFinite(parsed)) return 12;
  const normalized = Math.trunc(parsed);
  if (normalized < 3) return 3;
  if (normalized > 24) return 24;
  return normalized;
}

export async function GET(request: NextRequest) {
  const months = sanitizeMonths(request.nextUrl.searchParams.get("months"));
  const rawStatusScope = request.nextUrl.searchParams.get("status_scope");
  const statusScope: DashboardStatusScope =
    rawStatusScope && STATUS_SCOPES.includes(rawStatusScope as DashboardStatusScope)
      ? (rawStatusScope as DashboardStatusScope)
      : "all";
  const assigneeScope = sanitizeAssigneeScope(request.nextUrl.searchParams.get("assignee_scope"));

  const result = await runWithWorkspaceSession(request, async (context) => {
    await assertAccess(context, "orders.read");
    return getDashboardAnalytics(context, months, statusScope, assigneeScope);
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}
