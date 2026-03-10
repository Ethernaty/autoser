"use client";

import { usePermissions } from "@/features/rbac/hooks/use-permissions";
import { usePlanCapabilities } from "@/features/subscription/hooks/use-plan-capabilities";
import type { PermissionAction } from "@/features/rbac/types/rbac-types";
import type { PlanLimitType } from "@/features/subscription/types/subscription-types";

type AccessCheckOptions = {
  limitType?: PlanLimitType;
  increment?: number;
};

export function useAccess() {
  const { can } = usePermissions();
  const { canConsumeLimit, capabilities } = usePlanCapabilities();

  const canAccess = (permission: PermissionAction, options?: AccessCheckOptions): boolean => {
    if (!can(permission)) {
      return false;
    }

    if (!options?.limitType) {
      return true;
    }

    return canConsumeLimit(options.limitType, options.increment ?? 1);
  };

  return {
    canAccess,
    capabilities
  };
}
