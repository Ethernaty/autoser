import { NextRequest, NextResponse } from "next/server";

import {
  BackendApiError,
  meWithBackend,
  refreshWithBackend
} from "@/features/auth/api/server-auth";
import {
  ACCESS_COOKIE_NAME,
  clearSessionCookies,
  REFRESH_COOKIE_NAME,
  setActiveWorkspaceCookie,
  setSessionCookies
} from "@/features/auth/api/session-cookies";
import { resolveForwardedFor } from "@/shared/security/forwarded-for";

export async function GET(request: NextRequest): Promise<NextResponse> {
  const accessToken = request.cookies.get(ACCESS_COOKIE_NAME)?.value;
  const refreshToken = request.cookies.get(REFRESH_COOKIE_NAME)?.value;
  const forwardedFor = resolveForwardedFor(request);

  if (!accessToken) {
    const response = NextResponse.json({ message: "Unauthorized" }, { status: 401 });
    clearSessionCookies(response);
    return response;
  }

  try {
    const session = await meWithBackend(accessToken, forwardedFor);
    const response = NextResponse.json(session);
    setActiveWorkspaceCookie(response, session.workspaceId);
    return response;
  } catch (error) {
    if (!(error instanceof BackendApiError) || error.status !== 401 || !refreshToken) {
      if (error instanceof BackendApiError && error.status !== 401) {
        return NextResponse.json(error.payload ?? { message: error.message }, { status: error.status });
      }

      const response = NextResponse.json({ message: "Unauthorized" }, { status: 401 });
      clearSessionCookies(response);
      return response;
    }

    try {
      const refreshedTokens = await refreshWithBackend(refreshToken, forwardedFor);
      const session = await meWithBackend(refreshedTokens.access_token, forwardedFor);
      const response = NextResponse.json(session);
      setSessionCookies(response, refreshedTokens);
      setActiveWorkspaceCookie(response, session.workspaceId);
      return response;
    } catch (refreshError) {
      if (refreshError instanceof BackendApiError && refreshError.status !== 401) {
        return NextResponse.json(refreshError.payload ?? { message: refreshError.message }, { status: refreshError.status });
      }

      const response = NextResponse.json({ message: "Unauthorized" }, { status: 401 });
      clearSessionCookies(response);
      return response;
    }
  }
}

