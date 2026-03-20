import type { WorkspaceRole } from "@/features/rbac/types/rbac-types";

const BACKEND_ROLE_ALIASES: Readonly<Record<string, WorkspaceRole>> = {
  owner: "owner",
  admin: "admin",
  manager: "manager",
  employee: "employee",
  mechanic: "employee"
};

export function normalizeWorkspaceRole(rawRole: string): WorkspaceRole | null {
  const normalized = rawRole.trim().toLowerCase();
  return BACKEND_ROLE_ALIASES[normalized] ?? null;
}
