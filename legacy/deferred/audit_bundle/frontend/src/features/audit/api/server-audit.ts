import "server-only";

import { backendRequest } from "@/shared/api/backend-client";
import { WorkspaceScopeError } from "@/shared/errors/workspace-scope-error";
import type { AuditListParams, AuditPage } from "@/features/audit/types/audit-types";
import type { WorkspaceContext } from "@/features/auth/api/backend-session";

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

function assertWorkspaceContext(context: WorkspaceContext, workspaceId: string): void {
  if (workspaceId !== context.workspaceId) {
    throw new WorkspaceScopeError({
      expectedWorkspaceId: context.workspaceId,
      actualWorkspaceId: workspaceId,
      entity: "audit_record"
    });
  }
}

export async function listAuditLogs(context: WorkspaceContext, params: AuditListParams): Promise<AuditPage> {
  const query = new URLSearchParams();
  query.set("limit", String(params.limit ?? 25));
  query.set("offset", String(params.offset ?? 0));

  if (params.level) {
    query.set("level", params.level);
  }
  if (params.q) {
    query.set("q", params.q);
  }

  const payload = await backendRequest<{
    items: Array<{
      id: string;
      user_id: string;
      workspace_id: string;
      entity: string;
      entity_id: string | null;
      action: string;
      previous_value: Record<string, unknown> | null;
      new_value: Record<string, unknown> | null;
      metadata: Record<string, unknown>;
      timestamp: string;
    }>;
    limit: number;
    offset: number;
    has_next: boolean;
  }>(`/audit/?${query.toString()}`, {
    method: "GET",
    headers: authHeader(context)
  });

  return {
    items: payload.items.map((item) => {
      assertWorkspaceContext(context, item.workspace_id);

      return {
        id: item.id,
        userId: item.user_id,
        workspaceId: item.workspace_id,
        entity: item.entity,
        entityId: item.entity_id,
        action: item.action,
        previousValue: item.previous_value,
        newValue: item.new_value,
        metadata: item.metadata,
        timestamp: item.timestamp
      };
    }),
    limit: payload.limit,
    offset: payload.offset,
    hasNext: payload.has_next
  };
}


