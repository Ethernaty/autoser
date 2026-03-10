import "server-only";

import { backendRequest } from "@/shared/api/backend-client";
import type { WorkspaceContext } from "@/features/auth/api/backend-session";

type BackendSubscriptionCurrent = {
  id: string;
  tenant_id: string;
  plan_id: string;
  status: string;
  current_period_start: string;
  current_period_end: string;
  trial_end: string | null;
  created_at: string;
  updated_at: string;
};

type BackendPlan = {
  id: string;
  name: string;
  price: number | string;
  limits: Record<string, unknown>;
  features: Record<string, unknown>;
  is_active: boolean;
  description?: string | null;
};

function authHeader(context: WorkspaceContext): Record<string, string> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${context.accessToken}`,
    "X-Workspace-Id": context.workspaceId
  };
  if (context.forwardedFor) {
    headers["X-Forwarded-For"] = context.forwardedFor;
  }
  return headers;
}

export async function fetchSubscriptionCurrent(context: WorkspaceContext): Promise<BackendSubscriptionCurrent> {
  return backendRequest<BackendSubscriptionCurrent>("/subscription/current", {
    method: "GET",
    headers: authHeader(context)
  });
}

export async function fetchSubscriptionPlans(context: WorkspaceContext): Promise<BackendPlan[]> {
  return backendRequest<BackendPlan[]>("/subscription/plans", {
    method: "GET",
    headers: authHeader(context)
  });
}

export type BackendUsageQuota = {
  resource: string;
  used: number;
  hard_limit: number;
  remaining: number;
  soft_warning: boolean;
  period_start: string;
};

export async function fetchSubscriptionUsage(
  context: WorkspaceContext,
  resource: string
): Promise<BackendUsageQuota> {
  return backendRequest<BackendUsageQuota>(`/subscription/usage/${resource}`, {
    method: "GET",
    headers: authHeader(context)
  });
}
