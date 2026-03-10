import "server-only";

import { LIMIT_TO_COUNTER } from "@/features/subscription/config/usage-mapping";
import type { PlanLimitType, PlanUsageCheck, SubscriptionSnapshot } from "@/features/subscription/types/subscription-types";
import { PlanAccessDeniedError } from "@/shared/errors/plan-access-denied-error";
import { PlanLimitExceededError } from "@/shared/errors/plan-limit-exceeded-error";

function resolveCurrentUsage(snapshot: SubscriptionSnapshot, limitType: PlanLimitType): number {
  const counter = LIMIT_TO_COUNTER[limitType];
  return snapshot.usage[counter];
}

function assertSubscriptionStatus(snapshot: SubscriptionSnapshot): void {
  const status = snapshot.subscription.status;
  if (status === "active" || status === "trial") {
    return;
  }

  throw new PlanAccessDeniedError(`Subscription status ${status} blocks this action`);
}

export function assertPlanLimit(snapshot: SubscriptionSnapshot, check: PlanUsageCheck): void {
  assertSubscriptionStatus(snapshot);

  const projectedIncrement = check.projectedIncrement ?? 1;
  const hardLimit = snapshot.planDefinition.usageLimits[check.limitType];

  if (hardLimit === "unlimited") {
    return;
  }

  const currentUsage = resolveCurrentUsage(snapshot, check.limitType);
  const nextUsage = currentUsage + Math.max(0, projectedIncrement);

  if (nextUsage <= hardLimit) {
    return;
  }

  throw new PlanLimitExceededError({
    limitType: check.limitType,
    message: `Limit ${check.limitType} exceeded for plan ${snapshot.planDefinition.plan}`
  });
}
