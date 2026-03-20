import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { getWorkspaceSettings, patchWorkspaceSettings } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function GET(request: NextRequest) {
  const result = await runWithWorkspaceSession(request, async (context) => {
    await assertAccess(context, "workspace_settings.read");
    return getWorkspaceSettings(context);
  });

  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}

export async function PATCH(request: NextRequest) {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  let payload: {
    service_name?: string;
    phone?: string;
    address?: string | null;
    timezone?: string;
    currency?: string;
    working_hours_note?: string | null;
  };

  try {
    payload = (await request.json()) as {
      service_name?: string;
      phone?: string;
      address?: string | null;
      timezone?: string;
      currency?: string;
      working_hours_note?: string | null;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (context) => {
    await assertAccess(context, "workspace_settings.manage");
    return patchWorkspaceSettings(context, payload);
  });

  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
