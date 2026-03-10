"use client";

import type { ReactNode } from "react";

import { usePermissions } from "@/features/rbac/hooks/use-permissions";
import type { PermissionAction } from "@/features/rbac/types/rbac-types";

type FeatureGuardProps = {
  action: PermissionAction;
  fallback?: ReactNode;
  children: ReactNode;
};

export function FeatureGuard({ action, fallback = null, children }: FeatureGuardProps): JSX.Element | null {
  const { can } = usePermissions();

  if (!can(action)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

type DisableGuardProps = {
  action: PermissionAction;
  children: (disabled: boolean) => ReactNode;
};

export function DisableIfForbidden({ action, children }: DisableGuardProps): JSX.Element {
  const { can } = usePermissions();
  return <>{children(!can(action))}</>;
}
