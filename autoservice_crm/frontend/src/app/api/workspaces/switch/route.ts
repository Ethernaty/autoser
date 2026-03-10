import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession } from "@/features/auth/api/backend-session";
import { switchWorkspaceWithBackend, toAuthSession } from "@/features/auth/api/server-auth";
import { setActiveWorkspaceCookie, setSessionCookies } from "@/features/auth/api/session-cookies";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function POST(request: NextRequest) {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  let payload: {
    workspaceId?: string;
  };

  try {
    payload = (await request.json()) as {
      workspaceId?: string;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.workspaceId) {
    return NextResponse.json({ message: "workspaceId is required" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (context) => {
    const authResponse = await switchWorkspaceWithBackend(context.accessToken, payload.workspaceId!, context.forwardedFor);
    const session = toAuthSession({
      user: authResponse.user,
      tenant: authResponse.tenant,
      role: authResponse.role
    });

    return {
      session,
      tokens: authResponse.tokens
    };
  });

  if ("status" in result) {
    return result;
  }

  const response = NextResponse.json(result.data.session);
  setSessionCookies(response, result.data.tokens);
  setActiveWorkspaceCookie(response, result.data.session.workspaceId);
  return response;
}

