import { NextRequest } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { buildPlanCapabilities } from "@/features/subscription/server/plan-capabilities";
import { getWorkspaceSubscriptionSnapshot } from "@/features/subscription/server/subscription-service";
import type { SubscriptionQueryResponse } from "@/features/subscription/types/subscription-types";

export async function GET(request: NextRequest) {
  const result = await runWithWorkspaceSession(request, async (context) => {
    const snapshot = await getWorkspaceSubscriptionSnapshot(context);
    const response: SubscriptionQueryResponse = {
      subscription: snapshot.subscription,
      planDefinition: snapshot.planDefinition,
      usage: snapshot.usage,
      capabilities: buildPlanCapabilities(snapshot)
    };

    return response;
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}
