import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { listWorkspacesWithBackend } from "@/features/auth/api/server-auth";
import { WorkspaceScopeError } from "@/shared/errors/workspace-scope-error";

export async function GET(request: NextRequest) {
  const result = await runWithWorkspaceSession(request, async (context) => {
    const payload = await listWorkspacesWithBackend(context.accessToken, context.forwardedFor);

    if (payload.activeWorkspaceId !== context.workspaceId) {
      throw new WorkspaceScopeError({
        expectedWorkspaceId: context.workspaceId,
        actualWorkspaceId: payload.activeWorkspaceId,
        entity: "workspace_list"
      });
    }

    return payload;
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}

