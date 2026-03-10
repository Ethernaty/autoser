import type { WorkspaceRole } from "@/features/rbac/types/rbac-types";
import type { WorkspaceScoped } from "@/shared/types/workspace";

export type AuthUser = {
  id: string;
  email: string;
  is_active: boolean;
};

export type AuthTenant = {
  id: string;
  name: string;
  slug: string;
  state?: string;
};

export type AuthSession = WorkspaceScoped & {
  user: AuthUser;
  tenant: AuthTenant;
  role: WorkspaceRole;
};

export type WorkspaceMembership = {
  id: string;
  name: string;
  slug: string;
  role: WorkspaceRole;
  isActive: boolean;
};

export type WorkspaceListResponse = {
  activeWorkspaceId: string;
  workspaces: WorkspaceMembership[];
};

export type LoginPayload = {
  email: string;
  password: string;
  tenantSlug?: string;
};

export type BackendTokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  access_expires_in: number;
  refresh_expires_in: number;
};

export type BackendLoginResponse = {
  user: AuthUser;
  tenant: AuthTenant;
  role: string;
  tokens: BackendTokenPair;
};

export type BackendRefreshResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  access_expires_in: number;
  refresh_expires_in: number;
};
