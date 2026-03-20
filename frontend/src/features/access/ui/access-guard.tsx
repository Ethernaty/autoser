"use client";

import type { ReactNode } from "react";

import { useAccess } from "@/features/access/hooks/use-access";
import type { PermissionAction } from "@/features/rbac/types/rbac-types";

type AccessGuardProps = {
  permission: PermissionAction;
  limitType?: string;
  increment?: number;
  fallback?: ReactNode;
  children: ReactNode;
};

export function AccessGuard({ permission, limitType, increment, fallback = null, children }: AccessGuardProps): JSX.Element | null {
  const { canAccess } = useAccess();

  if (!canAccess(permission, { limitType, increment })) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

type DisableIfNoAccessProps = {
  permission: PermissionAction;
  limitType?: string;
  increment?: number;
  children: (disabled: boolean, onUpgrade: () => void) => ReactNode;
};

export function DisableIfNoAccess({ permission, limitType, increment, children }: DisableIfNoAccessProps): JSX.Element {
  const { canAccess } = useAccess();
  const allowed = canAccess(permission, { limitType, increment });

  return <>{children(!allowed, () => undefined)}</>;
}
