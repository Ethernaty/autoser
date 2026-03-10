import "server-only";

import { normalizeWorkspaceRole } from "@/features/rbac/config/role-mapping";
import type { WorkspaceRole } from "@/features/rbac/types/rbac-types";
import { backendRequest, BackendApiError } from "@/shared/api/backend-client";
import type {
  AuthSession,
  BackendLoginResponse,
  BackendRefreshResponse,
  LoginPayload,
  WorkspaceListResponse
} from "@/features/auth/types/auth-types";

export { BackendApiError };

function authHeader(accessToken: string, forwardedFor?: string): Record<string, string> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${accessToken}`
  };
  if (forwardedFor) {
    headers["X-Forwarded-For"] = forwardedFor;
  }
  return headers;
}

function toWorkspaceRole(rawRole: string): WorkspaceRole {
  const normalized = normalizeWorkspaceRole(rawRole);
  if (!normalized) {
    throw new BackendApiError("Unsupported workspace role", 403, {
      code: "unsupported_workspace_role",
      message: "Unsupported workspace role"
    });
  }

  return normalized;
}

export function toAuthSession(payload: {
  user: AuthSession["user"];
  tenant: AuthSession["tenant"];
  role: string;
}): AuthSession {
  return {
    user: payload.user,
    tenant: payload.tenant,
    role: toWorkspaceRole(payload.role),
    workspaceId: payload.tenant.id
  };
}

export async function loginWithBackend(payload: LoginPayload, forwardedFor?: string): Promise<BackendLoginResponse> {
  return backendRequest<BackendLoginResponse>("/auth/login", {
    method: "POST",
    headers: forwardedFor ? { "X-Forwarded-For": forwardedFor } : undefined,
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      tenant_slug: payload.tenantSlug ?? null
    })
  });
}

export async function logoutWithBackend(refreshToken: string, forwardedFor?: string): Promise<void> {
  await backendRequest<void>("/auth/logout", {
    method: "POST",
    headers: forwardedFor ? { "X-Forwarded-For": forwardedFor } : undefined,
    body: JSON.stringify({
      refresh_token: refreshToken
    })
  });
}

export async function refreshWithBackend(
  refreshToken: string,
  forwardedFor?: string
): Promise<BackendRefreshResponse> {
  return backendRequest<BackendRefreshResponse>("/auth/refresh", {
    method: "POST",
    headers: forwardedFor ? { "X-Forwarded-For": forwardedFor } : undefined,
    body: JSON.stringify({
      refresh_token: refreshToken
    })
  });
}

export async function meWithBackend(accessToken: string, forwardedFor?: string): Promise<AuthSession> {
  const payload = await backendRequest<{ user: AuthSession["user"]; tenant: AuthSession["tenant"]; role: string }>("/auth/me", {
    method: "GET",
    headers: authHeader(accessToken, forwardedFor)
  });
  return toAuthSession(payload);
}

export async function listWorkspacesWithBackend(
  accessToken: string,
  forwardedFor?: string
): Promise<WorkspaceListResponse> {
  const payload = await backendRequest<{
    active_workspace_id: string;
    workspaces: Array<{
      id: string;
      name: string;
      slug: string;
      role: string;
      is_active: boolean;
    }>;
  }>("/auth/workspaces", {
    method: "GET",
    headers: authHeader(accessToken, forwardedFor)
  });

  return {
    activeWorkspaceId: payload.active_workspace_id,
    workspaces: payload.workspaces.map((item) => ({
      id: item.id,
      name: item.name,
      slug: item.slug,
      role: toWorkspaceRole(item.role),
      isActive: item.is_active
    }))
  };
}

export async function switchWorkspaceWithBackend(
  accessToken: string,
  workspaceId: string,
  forwardedFor?: string
): Promise<BackendLoginResponse> {
  return backendRequest<BackendLoginResponse>("/auth/switch-workspace", {
    method: "POST",
    headers: authHeader(accessToken, forwardedFor),
    body: JSON.stringify({
      workspace_id: workspaceId
    })
  });
}
