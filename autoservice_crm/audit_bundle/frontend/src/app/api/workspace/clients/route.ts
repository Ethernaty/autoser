import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession, withSessionJson } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { createClient, listClients } from "@/features/workspace/api/server-workspace";
import { enforceSameOrigin } from "@/shared/security/origin";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q") ?? "";
  const limit = Number(request.nextUrl.searchParams.get("limit") ?? "20");
  const offset = Number(request.nextUrl.searchParams.get("offset") ?? "0");

  const result = await runWithWorkspaceSession(request, async (context) =>
    listClients(context, {
      q: query,
      limit,
      offset
    })
  );

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
    name?: string;
    phone?: string;
    email?: string | null;
    comment?: string | null;
  };

  try {
    payload = (await request.json()) as {
      name?: string;
      phone?: string;
      email?: string | null;
      comment?: string | null;
    };
  } catch {
    return NextResponse.json({ message: "Invalid request payload" }, { status: 400 });
  }

  if (!payload.name?.trim() || !payload.phone?.trim()) {
    return NextResponse.json({ message: "Name and phone are required" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (context) => {
    await assertAccess(context, "clients.create");

    const client = await createClient(context, {
      name: payload.name!.trim(),
      phone: payload.phone!.trim(),
      email: payload.email ?? null,
      comment: payload.comment ?? null
    }, { idempotencyKey });

    return client;
  });

  if ("status" in result) {
    return result;
  }

  return withSessionJson(result);
}

