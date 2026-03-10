"use client";

import { useMemo } from "react";

import { useSubscriptionQuery } from "@/features/subscription/hooks/use-subscription-query";
import type { PlanFeatureFlag, PlanLimitType } from "@/features/subscription/types/subscription-types";

export function usePlanCapabilities() {
  const subscriptionQuery = useSubscriptionQuery();

  const capabilities = useMemo(() => {
    return subscriptionQuery.data?.capabilities ?? null;
  }, [subscriptionQuery.data?.capabilities]);

  const canUseFeature = (feature: PlanFeatureFlag): boolean => {
    if (!capabilities) {
      return false;
    }

    return capabilities.featureFlags[feature];
  };

  const canConsumeLimit = (limitType: PlanLimitType, increment = 1): boolean => {
    if (!capabilities) {
      return false;
    }

    const remaining = capabilities.remaining[limitType];
    if (remaining === "unlimited") {
      return true;
    }

    return remaining >= increment;
  };

  return {
    ...subscriptionQuery,
    capabilities,
    canUseFeature,
    canConsumeLimit
  };
}
