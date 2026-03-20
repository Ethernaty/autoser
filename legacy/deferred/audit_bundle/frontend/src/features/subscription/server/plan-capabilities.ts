import "server-only";

import type { PlanCapabilities, PlanLimitType, SubscriptionSnapshot } from "@/features/subscription/types/subscription-types";
import { LIMIT_TO_COUNTER } from "@/features/subscription/config/usage-mapping";

function remainingForLimit(snapshot: SubscriptionSnapshot, limitType: PlanLimitType): number | "unlimited" {
  const limit = snapshot.planDefinition.usageLimits[limitType];
  if (limit === "unlimited") {
    return "unlimited";
  }

  const counter = LIMIT_TO_COUNTER[limitType];
  const used = snapshot.usage[counter];
  return Math.max(0, limit - used);
}

export function buildPlanCapabilities(snapshot: SubscriptionSnapshot): PlanCapabilities {
  return {
    plan: snapshot.subscription.plan,
    status: snapshot.subscription.status,
    featureFlags: snapshot.planDefinition.featureFlags,
    usageLimits: snapshot.planDefinition.usageLimits,
    usage: snapshot.usage,
    remaining: {
      maxUsers: remainingForLimit(snapshot, "maxUsers"),
      maxOrdersPerMonth: remainingForLimit(snapshot, "maxOrdersPerMonth"),
      maxPaymentsPerMonth: remainingForLimit(snapshot, "maxPaymentsPerMonth")
    }
  };
}
