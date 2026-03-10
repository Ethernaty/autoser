import "server-only";

import { normalizeWorkspaceRole } from "@/features/rbac/config/role-mapping";
import { backendRequest } from "@/shared/api/backend-client";
import { WorkspaceScopeError } from "@/shared/errors/workspace-scope-error";
import type { WorkspaceContext } from "@/features/auth/api/backend-session";

type BackendWorkspaceUserRecord = {
  user_id: string;
  tenant_id: string;
  email: string;
  role: string;
  created_at: string;
};

export type WorkspaceUserRecord = {
  id: string;
  tenantId: string;
  email: string;
  role: "owner" | "admin" | "manager" | "employee";
  createdAt: string;
};

function authHeader(context: WorkspaceContext): Record<string, string> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${context.accessToken}`,
    "X-Workspace-Id": context.workspaceId
  };
  if (context.forwardedFor) {
    headers["X-Forwarded-For"] = context.forwardedFor;
  }
  return headers;
}

export async function createWorkspaceUser(
  context: WorkspaceContext,
  payload: {
    email: string;
    password: string;
    role: "owner" | "admin" | "manager" | "employee";
  },
  options?: { idempotencyKey?: string }
): Promise<WorkspaceUserRecord> {
  const headers = authHeader(context);
  if (options?.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }

  const record = await backendRequest<BackendWorkspaceUserRecord>("/users/", {
    method: "POST",
    headers,
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      role: payload.role
    })
  });

  if (record.tenant_id !== context.workspaceId) {
    throw new WorkspaceScopeError({
      expectedWorkspaceId: context.workspaceId,
      actualWorkspaceId: record.tenant_id,
      entity: "workspace_user"
    });
  }

  const role = normalizeWorkspaceRole(record.role);
  if (!role) {
    throw new Error("Unsupported backend user role");
  }

  return {
    id: record.user_id,
    tenantId: record.tenant_id,
    email: record.email,
    role,
    createdAt: record.created_at
  };
}
