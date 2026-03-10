import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { createWorkspaceUser } from "@/features/workspace/api/server-workspace-users";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function POST(request: NextRequest) {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  const idempotencyKey = request.headers.get("Idempotency-Key") ?? undefined;

  let payload: {
    email?: string;
    password?: string;
    role?: "owner" | "admin" | "manager" | "employee";
  };

  try {
    payload = (await request.json()) as {
      email?: string;
      password?: string;
      role?: "owner" | "admin" | "manager" | "employee";
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.email || !payload.password || !payload.role) {
    return NextResponse.json({ message: "email, password and role are required" }, { status: 400 });
  }

  const email = payload.email;
  const password = payload.password;
  const role = payload.role;

  const result = await runWithWorkspaceSession(request, async (context) => {
    await assertAccess(context, "workspace.settings.manage");

    const createdUser = await createWorkspaceUser(context, {
      email,
      password,
      role
    }, { idempotencyKey });

    return createdUser;
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}
