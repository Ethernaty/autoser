import { NextRequest, NextResponse } from "next/server";

import { BackendApiError, logoutWithBackend } from "@/features/auth/api/server-auth";
import {
  clearSessionCookies,
  REFRESH_COOKIE_NAME
} from "@/features/auth/api/session-cookies";
import { resolveForwardedFor } from "@/shared/security/forwarded-for";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  const refreshToken = request.cookies.get(REFRESH_COOKIE_NAME)?.value;

  if (refreshToken) {
    try {
      const forwardedFor = resolveForwardedFor(request);
      await logoutWithBackend(refreshToken, forwardedFor);
    } catch (error) {
      if (!(error instanceof BackendApiError)) {
        // Ignore unknown backend logout failure and continue cleanup.
      }
    }
  }

  const response = new NextResponse(null, { status: 204 });
  clearSessionCookies(response);
  return response;
}
