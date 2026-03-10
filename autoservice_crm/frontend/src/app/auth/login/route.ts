import { NextResponse } from "next/server";

import { BackendApiError, loginWithBackend, toAuthSession } from "@/features/auth/api/server-auth";
import { setActiveWorkspaceCookie, setSessionCookies } from "@/features/auth/api/session-cookies";
import type { LoginPayload } from "@/features/auth/types/auth-types";
import { resolveForwardedFor } from "@/shared/security/forwarded-for";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function POST(request: Request): Promise<NextResponse> {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  let payload: LoginPayload;

  try {
    payload = (await request.json()) as LoginPayload;
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.email || !payload.password) {
    return NextResponse.json({ message: "Email and password are required" }, { status: 400 });
  }

  try {
    const forwardedFor = resolveForwardedFor(request);
    const authResponse = await loginWithBackend(payload, forwardedFor);
    const session = toAuthSession({
      user: authResponse.user,
      tenant: authResponse.tenant,
      role: authResponse.role
    });

    const response = NextResponse.json(session);
    setSessionCookies(response, authResponse.tokens);
    setActiveWorkspaceCookie(response, session.workspaceId);
    return response;
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(error.payload ?? { message: error.message }, { status: error.status });
    }

    return NextResponse.json({ message: "Login request failed" }, { status: 500 });
  }
}

