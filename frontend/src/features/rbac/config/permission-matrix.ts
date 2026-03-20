import type { PermissionAction, WorkspaceRole } from "@/features/rbac/types/rbac-types";

export const PERMISSION_MATRIX: Readonly<Record<WorkspaceRole, readonly PermissionAction[]>> = {
  owner: [
    "clients.read",
    "clients.create",
    "clients.update",
    "vehicles.read",
    "vehicles.create",
    "vehicles.update",
    "employees.read",
    "employees.create",
    "employees.update",
    "employees.delete",
    "orders.read",
    "orders.create",
    "orders.update",
    "orders.delete",
    "orders.change_status",
    "orders.assign",
    "orders.close",
    "payments.read",
    "payments.create",
    "workspace_settings.read",
    "workspace_settings.manage",
    "audit.read"
  ],
  admin: [
    "clients.read",
    "clients.create",
    "clients.update",
    "vehicles.read",
    "vehicles.create",
    "vehicles.update",
    "employees.read",
    "employees.create",
    "employees.update",
    "employees.delete",
    "orders.read",
    "orders.create",
    "orders.update",
    "orders.delete",
    "orders.change_status",
    "orders.assign",
    "orders.close",
    "payments.read",
    "payments.create",
    "workspace_settings.read",
    "workspace_settings.manage",
    "audit.read"
  ],
  manager: [
    "clients.read",
    "clients.create",
    "clients.update",
    "vehicles.read",
    "vehicles.create",
    "vehicles.update",
    "employees.read",
    "orders.read",
    "orders.create",
    "orders.update",
    "orders.change_status",
    "orders.assign",
    "orders.close",
    "payments.read",
    "payments.create",
    "workspace_settings.read",
    "audit.read"
  ],
  employee: [
    "clients.read",
    "vehicles.read",
    "employees.read",
    "orders.read",
    "orders.create",
    "orders.update",
    "orders.change_status",
    "payments.read",
    "payments.create",
    "workspace_settings.read"
  ]
};

const ACTION_ALIASES: Readonly<Record<PermissionAction, PermissionAction>> = {
  "clients.read": "clients.read",
  "clients.create": "clients.create",
  "clients.update": "clients.update",
  "vehicles.read": "vehicles.read",
  "vehicles.create": "vehicles.create",
  "vehicles.update": "vehicles.update",
  "employees.read": "employees.read",
  "employees.create": "employees.create",
  "employees.update": "employees.update",
  "employees.delete": "employees.delete",
  "orders.read": "orders.read",
  "orders.create": "orders.create",
  "orders.update": "orders.update",
  "orders.delete": "orders.delete",
  "orders.change_status": "orders.change_status",
  "orders.assign": "orders.assign",
  "orders.close": "orders.close",
  "payments.read": "payments.read",
  "payments.create": "payments.create",
  "workspace_settings.read": "workspace_settings.read",
  "workspace_settings.manage": "workspace_settings.manage",
  "audit.read": "audit.read",
  "orders.edit": "orders.update",
  "clients.edit": "clients.update",
  "finance.create_payment": "payments.create",
  "finance.refund": "payments.create",
  "workspace.settings.manage": "workspace_settings.manage"
};

function normalizePermissionAction(action: PermissionAction): PermissionAction {
  return ACTION_ALIASES[action] ?? action;
}

const PERMISSION_SETS: Readonly<Record<WorkspaceRole, ReadonlySet<PermissionAction>>> = {
  owner: new Set(PERMISSION_MATRIX.owner.map(normalizePermissionAction)),
  manager: new Set(PERMISSION_MATRIX.manager.map(normalizePermissionAction)),
  admin: new Set(PERMISSION_MATRIX.admin.map(normalizePermissionAction)),
  employee: new Set(PERMISSION_MATRIX.employee.map(normalizePermissionAction))
};

export function getRolePermissions(role: WorkspaceRole): readonly PermissionAction[] {
  return PERMISSION_MATRIX[role];
}

export function hasPermission(role: WorkspaceRole, action: PermissionAction): boolean {
  return PERMISSION_SETS[role].has(normalizePermissionAction(action));
}
