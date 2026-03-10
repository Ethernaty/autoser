import "server-only";

import type { WorkspaceContext } from "@/features/auth/api/backend-session";
import { hasPermission } from "@/features/rbac/config/permission-matrix";
import type { PermissionAction } from "@/features/rbac/types/rbac-types";
import { RbacForbiddenError } from "@/shared/errors/rbac-forbidden-error";

export function assertWorkspacePermission(context: WorkspaceContext, action: PermissionAction): void {
  if (!hasPermission(context.role, action)) {
    throw new RbacForbiddenError(action, context.role);
  }
}
