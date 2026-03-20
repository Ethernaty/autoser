"use client";

import { useMemo } from "react";

import { useAuthStore } from "@/features/auth/model/auth-store";
import { getRolePermissions, hasPermission } from "@/features/rbac/config/permission-matrix";
import type { PermissionAction } from "@/features/rbac/types/rbac-types";

export function usePermissions() {
  const role = useAuthStore((state) => state.session?.role ?? null);

  const permissions = useMemo(() => {
    if (!role) {
      return [] as const;
    }

    return getRolePermissions(role);
  }, [role]);

  const can = (action: PermissionAction): boolean => {
    if (!role) {
      return false;
    }

    return hasPermission(role, action);
  };

  return {
    role,
    permissions,
    can
  };
}
