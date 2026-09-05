import { NextRequest, NextResponse } from "next/server";

import { BackendApiError, changePasswordWithBackend } from "@/features/auth/api/server-auth";
import { ACCESS_COOKIE_NAME, clearSessionCookies } from "@/features/auth/api/session-cookies";
import { resolveForwardedFor } from "@/shared/security/forwarded-for";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const originError = enforceSameOrigin(request);
  if (originError) return originError;
  const accessToken = request.cookies.get(ACCESS_COOKIE_NAME)?.value;
  if (!accessToken) return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
  const body = (await request.json().catch(() => ({}))) as { currentPassword?: string; newPassword?: string };
  if (!body.currentPassword || !body.newPassword) return NextResponse.json({ message: "Both passwords are required" }, { status: 400 });
  try {
    await changePasswordWithBackend(accessToken, body.currentPassword, body.newPassword, resolveForwardedFor(request));
    const response = new NextResponse(null, { status: 204 });
    clearSessionCookies(response);
    return response;
  } catch (error) {
    if (error instanceof BackendApiError) return NextResponse.json(error.payload, { status: error.status });
    throw error;
  }
}
