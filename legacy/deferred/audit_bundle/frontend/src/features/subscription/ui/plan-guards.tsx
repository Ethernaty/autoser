"use client";

import type { ReactNode } from "react";

import { usePlanCapabilities } from "@/features/subscription/hooks/use-plan-capabilities";
import { useUpgradeModalStore } from "@/features/subscription/model/upgrade-modal-store";
import type { PlanFeatureFlag, PlanLimitType } from "@/features/subscription/types/subscription-types";

type PlanFeatureGuardProps = {
  feature: PlanFeatureFlag;
  fallback?: ReactNode;
  children: ReactNode;
};

export function PlanFeatureGuard({ feature, fallback = null, children }: PlanFeatureGuardProps): JSX.Element | null {
  const { canUseFeature } = usePlanCapabilities();

  if (!canUseFeature(feature)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

type DisableIfPlanLimitedProps = {
  limitType: PlanLimitType;
  increment?: number;
  children: (disabled: boolean, onUpgrade: () => void) => ReactNode;
};

export function DisableIfPlanLimited({ limitType, increment = 1, children }: DisableIfPlanLimitedProps): JSX.Element {
  const { canConsumeLimit } = usePlanCapabilities();
  const openForLimit = useUpgradeModalStore((state) => state.openForLimit);

  const allowed = canConsumeLimit(limitType, increment);

  return <>{children(!allowed, () => openForLimit(limitType))}</>;
}
