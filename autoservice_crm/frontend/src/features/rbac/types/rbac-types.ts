export const WORKSPACE_ROLES = ["owner", "admin", "manager", "employee"] as const;

export type WorkspaceRole = (typeof WORKSPACE_ROLES)[number];

export const PERMISSION_ACTIONS = [
  "orders.create",
  "orders.edit",
  "orders.delete",
  "orders.change_status",
  "finance.create_payment",
  "finance.refund",
  "clients.create",
  "clients.edit",
  "workspace.settings.manage"
] as const;

export type PermissionAction = (typeof PERMISSION_ACTIONS)[number];
