import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { createVehicle, listVehicles } from "@/features/workspace/api/server-mvp";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q") ?? "";
  const clientId = request.nextUrl.searchParams.get("client_id") ?? undefined;
  const limit = Number(request.nextUrl.searchParams.get("limit") ?? "20");
  const offset = Number(request.nextUrl.searchParams.get("offset") ?? "0");

  const result = await runWithWorkspaceSession(request, async (context) => {
    await assertAccess(context, "vehicles.read");
    return listVehicles(context, { q, client_id: clientId, limit, offset });
  });

  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}

export async function POST(request: NextRequest) {
  const originError = enforceSameOrigin(request);
  if (originError) {
    return originError;
  }

  const idempotencyKey = request.headers.get("Idempotency-Key") ?? undefined;

  let payload: {
    client_id?: string;
    plate_number?: string;
    make_model?: string;
    year?: number | null;
    vin?: string | null;
    comment?: string | null;
  };

  try {
    payload = (await request.json()) as {
      client_id?: string;
      plate_number?: string;
      make_model?: string;
      year?: number | null;
      vin?: string | null;
      comment?: string | null;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.client_id || !payload.plate_number || !payload.make_model) {
    return NextResponse.json({ message: "client_id, plate_number and make_model are required" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (context) => {
    await assertAccess(context, "vehicles.create");
    return createVehicle(
      context,
      {
        client_id: payload.client_id!,
        plate_number: payload.plate_number!.trim(),
        make_model: payload.make_model!.trim(),
        year: payload.year ?? null,
        vin: payload.vin ?? null,
        comment: payload.comment ?? null
      },
      { idempotencyKey }
    );
  });

  if ("status" in result) {
    return result;
  }
  return withSessionJson(result);
}
