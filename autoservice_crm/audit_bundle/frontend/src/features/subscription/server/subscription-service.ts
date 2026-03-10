import "server-only";

import { BACKEND_PLAN_ALIASES, PLAN_DEFINITIONS } from "@/features/subscription/config/plan-definitions";
import { fetchSubscriptionCurrent, fetchSubscriptionPlans } from "@/features/subscription/server/subscription-backend-api";
import { getWorkspaceUsage } from "@/features/subscription/server/usage-tracking-service";
import type { WorkspaceContext } from "@/features/auth/api/backend-session";
import type {
  PlanDefinition,
  SubscriptionPlan,
  SubscriptionSnapshot,
  SubscriptionStatus,
  WorkspaceSubscription
} from "@/features/subscription/types/subscription-types";

function normalizePlanName(rawName: string): SubscriptionPlan {
  const normalized = rawName.trim().toLowerCase();
  return BACKEND_PLAN_ALIASES[normalized] ?? "free";
}

function normalizeStatus(rawStatus: string): SubscriptionStatus {
  const normalized = rawStatus.trim().toLowerCase();

  if (normalized === "active" || normalized === "past_due" || normalized === "canceled" || normalized === "trial") {
    return normalized;
  }

  if (normalized === "suspended") {
    return "past_due";
  }

  return "past_due";
}

export async function getWorkspaceSubscriptionSnapshot(context: WorkspaceContext): Promise<SubscriptionSnapshot> {
  const [current, plans, usage] = await Promise.all([
    fetchSubscriptionCurrent(context),
    fetchSubscriptionPlans(context),
    getWorkspaceUsage(context)
  ]);

  const currentPlan = plans.find((plan) => plan.id === current.plan_id);
  const normalizedPlan = normalizePlanName(currentPlan?.name ?? "free");

  const subscription: WorkspaceSubscription = {
    workspaceId: context.workspaceId,
    plan: normalizedPlan,
    status: normalizeStatus(current.status),
    currentPeriodStart: current.current_period_start,
    currentPeriodEnd: current.current_period_end,
    trialEndsAt: current.trial_end,
    createdAt: current.created_at,
    updatedAt: current.updated_at
  };

  const planDefinition: PlanDefinition = PLAN_DEFINITIONS[normalizedPlan];

  return {
    subscription,
    planDefinition,
    usage
  };
}
