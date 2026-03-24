import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { getClient, patchClient } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function GET(
  request: NextRequest,
  context: {
    params: { clientId: string };
  }
) {
  const { clientId } = context.params;

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "clients.read");
    return getClient(workspaceContext, clientId);
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}

export async function PATCH(
  request: NextRequest,
  context: {
    params: { clientId: string };
  }
) {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  const { clientId } = context.params;

  let payload: {
    name?: string;
    phone?: string;
    email?: string | null;
    source?: string | null;
    comment?: string | null;
    version?: number;
  };

  try {
    payload = (await request.json()) as {
      name?: string;
      phone?: string;
      email?: string | null;
      source?: string | null;
      comment?: string | null;
      version?: number;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "clients.update");
    return patchClient(workspaceContext, clientId, payload);
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}
