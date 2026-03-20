"use client";

import type { ReactNode } from "react";

import { useAccess } from "@/features/access/hooks/use-access";
import { useUpgradeModalStore } from "@/features/subscription/model/upgrade-modal-store";
import type { PermissionAction } from "@/features/rbac/types/rbac-types";
import type { PlanLimitType } from "@/features/subscription/types/subscription-types";

type AccessGuardProps = {
  permission: PermissionAction;
  limitType?: PlanLimitType;
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
  limitType?: PlanLimitType;
  increment?: number;
  children: (disabled: boolean, onUpgrade: () => void) => ReactNode;
};

export function DisableIfNoAccess({ permission, limitType, increment, children }: DisableIfNoAccessProps): JSX.Element {
  const { canAccess } = useAccess();
  const openForLimit = useUpgradeModalStore((state) => state.openForLimit);

  const allowed = canAccess(permission, { limitType, increment });

  const onUpgrade = (): void => {
    if (!limitType) {
      return;
    }
    openForLimit(limitType);
  };

  return <>{children(!allowed, onUpgrade)}</>;
}
