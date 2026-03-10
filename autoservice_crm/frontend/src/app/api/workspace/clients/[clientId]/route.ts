import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { updateClient } from "@/features/workspace/api/server-workspace";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function PATCH(
  request: NextRequest,
  context: {
    params: {
      clientId: string;
    };
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
    comment?: string | null;
  };

  try {
    payload = (await request.json()) as {
      name?: string;
      phone?: string;
      email?: string | null;
      comment?: string | null;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "clients.edit");

    const updatedClient = await updateClient(workspaceContext, clientId, {
      name: payload.name?.trim(),
      phone: payload.phone?.trim(),
      email: payload.email,
      comment: payload.comment
    });

    return updatedClient;
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}
