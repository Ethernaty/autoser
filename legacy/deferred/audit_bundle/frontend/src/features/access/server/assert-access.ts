import "server-only";

import { assertWorkspacePermission } from "@/features/rbac/server/assert-workspace-permission";
import { getWorkspaceSubscriptionSnapshot } from "@/features/subscription/server/subscription-service";
import type { WorkspaceContext } from "@/features/auth/api/backend-session";
import type { PermissionAction } from "@/features/rbac/types/rbac-types";
import type { SubscriptionSnapshot } from "@/features/subscription/types/subscription-types";

export async function assertAccess(
  context: WorkspaceContext,
  permission: PermissionAction
): Promise<SubscriptionSnapshot> {
  assertWorkspacePermission(context, permission);

  const snapshot = await getWorkspaceSubscriptionSnapshot(context);

  return snapshot;
}
