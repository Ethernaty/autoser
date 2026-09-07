import { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { getDashboardPreferences, patchDashboardPreferences } from "@/features/workspace/api/server-mvp";
import type { DashboardFilters, DashboardLayout, DashboardMode } from "@/features/workspace/types/mvp-types";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function GET(request: NextRequest) {
  const result = await runWithWorkspaceSession(request, async (context) => {
    await assertAccess(context, "orders.read");
    return getDashboardPreferences(context);
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
    mode?: DashboardMode;
    filters_json?: DashboardFilters;
    layout_json?: DashboardLayout;
    reset_layout?: boolean;
    reset_filters?: boolean;
  };
  try {
    payload = (await request.json()) as {
      mode?: DashboardMode;
      filters_json?: DashboardFilters;
      layout_json?: DashboardLayout;
      reset_layout?: boolean;
      reset_filters?: boolean;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (context) => {
    await assertAccess(context, "orders.read");
    return patchDashboardPreferences(context, payload);
  });
  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
