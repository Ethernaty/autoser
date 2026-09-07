import "server-only";
import { NextRequest, NextResponse } from "next/server";
import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import type { PermissionAction } from "@/features/rbac/types/rbac-types";
import { backendRequest } from "@/shared/api/backend-client";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function directoryProxy(request: NextRequest, path: string, permissions: PermissionAction[]) {
  let body: string | undefined;
  if (request.method !== "GET") {
    const originError = enforceSameOrigin(request);
    if (originError) return originError;
    try { body = JSON.stringify(await request.json()); }
    catch { return NextResponse.json({ message: "Некорректные данные" }, { status: 400 }); }
  }
  const result = await runWithWorkspaceSession(request, async (context) => {
    for (const permission of permissions) await assertAccess(context, permission);
    return backendRequest(path + (request.method === "GET" ? request.nextUrl.search : ""), {
      method: request.method, body,
      headers: { Authorization: `Bearer ${context.accessToken}`, "X-Workspace-Id": context.workspaceId }
    });
  });
  return "status" in result ? result : withSessionJson(result);
}
