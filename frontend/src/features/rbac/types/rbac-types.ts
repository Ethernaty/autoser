export const WORKSPACE_ROLES = ["owner", "admin", "manager", "employee"] as const;

export type WorkspaceRole = (typeof WORKSPACE_ROLES)[number];

export const PERMISSION_ACTIONS = [
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
  "audit.read",
  "orders.edit",
  "clients.edit",
  "finance.create_payment",
  "finance.refund",
  "workspace.settings.manage"
] as const;

export type PermissionAction = (typeof PERMISSION_ACTIONS)[number];
