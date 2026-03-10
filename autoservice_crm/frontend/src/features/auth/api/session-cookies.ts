import "server-only";

import type { NextResponse } from "next/server";

import type { BackendLoginResponse, BackendRefreshResponse } from "@/features/auth/types/auth-types";

export const ACCESS_COOKIE_NAME = "as_access_token";
export const REFRESH_COOKIE_NAME = "as_refresh_token";
export const WORKSPACE_COOKIE_NAME = "as_workspace_id";

function secureCookie(): boolean {
  return process.env.NODE_ENV === "production";
}

export function setSessionCookies(
  response: NextResponse,
  tokens: BackendLoginResponse["tokens"] | BackendRefreshResponse
): void {
  response.cookies.set({
    name: ACCESS_COOKIE_NAME,
    value: tokens.access_token,
    httpOnly: true,
    secure: secureCookie(),
    sameSite: "lax",
    path: "/",
    maxAge: tokens.access_expires_in
  });

  response.cookies.set({
    name: REFRESH_COOKIE_NAME,
    value: tokens.refresh_token,
    httpOnly: true,
    secure: secureCookie(),
    sameSite: "lax",
    path: "/",
    maxAge: tokens.refresh_expires_in
  });
}

export function setActiveWorkspaceCookie(response: NextResponse, workspaceId: string): void {
  response.cookies.set({
    name: WORKSPACE_COOKIE_NAME,
    value: workspaceId,
    httpOnly: true,
    secure: secureCookie(),
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 14
  });
}

export function clearSessionCookies(response: NextResponse): void {
  response.cookies.set({
    name: ACCESS_COOKIE_NAME,
    value: "",
    path: "/",
    maxAge: 0,
    httpOnly: true,
    secure: secureCookie(),
    sameSite: "lax"
  });

  response.cookies.set({
    name: REFRESH_COOKIE_NAME,
    value: "",
    path: "/",
    maxAge: 0,
    httpOnly: true,
    secure: secureCookie(),
    sameSite: "lax"
  });

  response.cookies.set({
    name: WORKSPACE_COOKIE_NAME,
    value: "",
    path: "/",
    maxAge: 0,
    httpOnly: true,
    secure: secureCookie(),
    sameSite: "lax"
  });
}
