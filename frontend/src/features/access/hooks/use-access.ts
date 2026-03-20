"use client";

import { usePermissions } from "@/features/rbac/hooks/use-permissions";
import type { PermissionAction } from "@/features/rbac/types/rbac-types";

type AccessCheckOptions = {
  limitType?: string;
  increment?: number;
};

export function useAccess() {
  const { can } = usePermissions();

  const canAccess = (permission: PermissionAction, _options?: AccessCheckOptions): boolean => {
    return can(permission);
  };

  return {
    canAccess
  };
}
