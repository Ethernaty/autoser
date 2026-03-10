import "server-only";

import { fetchSubscriptionUsage } from "@/features/subscription/server/subscription-backend-api";
import type { WorkspaceContext } from "@/features/auth/api/backend-session";
import type { UsageCounterKey, WorkspaceUsage } from "@/features/subscription/types/subscription-types";

const USAGE_RESOURCE_MAP: Readonly<Record<UsageCounterKey, string>> = {
  ordersCreated: "orders",
  usersCount: "users",
  paymentsCount: "payments"
};

function monthKeyFromPeriod(periodStart: string | null | undefined): string {
  if (periodStart) {
    const parsed = new Date(periodStart);
    if (!Number.isNaN(parsed.getTime())) {
      return `${parsed.getUTCFullYear()}-${String(parsed.getUTCMonth() + 1).padStart(2, "0")}`;
    }
  }

  const now = new Date();
  return `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}`;
}

async function fetchUsageCount(context: WorkspaceContext, counter: UsageCounterKey): Promise<{ used: number; periodStart: string }> {
  const resource = USAGE_RESOURCE_MAP[counter];
  const usage = await fetchSubscriptionUsage(context, resource);
  return {
    used: usage.used,
    periodStart: usage.period_start
  };
}

export async function getWorkspaceUsage(context: WorkspaceContext): Promise<WorkspaceUsage> {
  const [ordersUsage, usersUsage, paymentsUsage] = await Promise.all([
    fetchUsageCount(context, "ordersCreated"),
    fetchUsageCount(context, "usersCount"),
    fetchUsageCount(context, "paymentsCount")
  ]);

  return {
    workspaceId: context.workspaceId,
    month: monthKeyFromPeriod(ordersUsage.periodStart),
    ordersCreated: ordersUsage.used,
    usersCount: usersUsage.used,
    paymentsCount: paymentsUsage.used
  };
}
