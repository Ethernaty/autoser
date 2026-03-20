import "server-only";

import { assertWorkspacePermission } from "@/features/rbac/server/assert-workspace-permission";
import type { WorkspaceContext } from "@/features/auth/api/backend-session";
import type { PermissionAction } from "@/features/rbac/types/rbac-types";

export async function assertAccess(context: WorkspaceContext, permission: PermissionAction): Promise<void> {
  assertWorkspacePermission(context, permission);
}
