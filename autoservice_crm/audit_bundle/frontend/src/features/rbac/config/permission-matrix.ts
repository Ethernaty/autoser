import type { PermissionAction, WorkspaceRole } from "@/features/rbac/types/rbac-types";

export const PERMISSION_MATRIX: Readonly<Record<WorkspaceRole, readonly PermissionAction[]>> = {
  owner: [
    "orders.create",
    "orders.edit",
    "orders.delete",
    "orders.change_status",
    "finance.create_payment",
    "finance.refund",
    "clients.create",
    "clients.edit",
    "workspace.settings.manage"
  ],
  admin: [
    "orders.create",
    "orders.edit",
    "orders.delete",
    "orders.change_status",
    "finance.create_payment",
    "finance.refund",
    "clients.create",
    "clients.edit",
    "workspace.settings.manage"
  ],
  manager: [
    "orders.create",
    "orders.edit",
    "orders.change_status",
    "finance.create_payment",
    "clients.edit"
  ],
  employee: ["orders.create", "orders.edit", "orders.change_status", "finance.create_payment"]
};

const PERMISSION_SETS: Readonly<Record<WorkspaceRole, ReadonlySet<PermissionAction>>> = {
  owner: new Set(PERMISSION_MATRIX.owner),
  manager: new Set(PERMISSION_MATRIX.manager),
  admin: new Set(PERMISSION_MATRIX.admin),
  employee: new Set(PERMISSION_MATRIX.employee)
};

export function getRolePermissions(role: WorkspaceRole): readonly PermissionAction[] {
  return PERMISSION_MATRIX[role];
}

export function hasPermission(role: WorkspaceRole, action: PermissionAction): boolean {
  return PERMISSION_SETS[role].has(action);
}
