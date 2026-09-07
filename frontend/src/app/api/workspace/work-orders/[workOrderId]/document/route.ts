import { NextRequest, NextResponse } from "next/server";

import { runWithWorkspaceSession } from "@/features/auth/api/backend-session";
import { assertAccess } from "@/features/access/server/assert-access";
import { serverEnv } from "@/core/config/server-env";

const ALLOWED_FORMATS = new Set(["pdf", "html", "docx"]);
const ALLOWED_LOCALES = new Set(["ru", "en"]);

function resolveAccept(format: string): string {
  if (format === "html") {
    return "text/html";
  }
  if (format === "docx") {
    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  }
  return "application/pdf";
}

export async function GET(
  request: NextRequest,
  context: {
    params: { workOrderId: string };
  }
) {
  const format = (request.nextUrl.searchParams.get("format") ?? "pdf").toLowerCase();
  const localeParam = (request.nextUrl.searchParams.get("locale") ?? "ru").toLowerCase();
  const locale = ALLOWED_LOCALES.has(localeParam) ? localeParam : "ru";
  if (!ALLOWED_FORMATS.has(format)) {
    return NextResponse.json({ message: "Unsupported format" }, { status: 400 });
  }

  const result = await runWithWorkspaceSession(request, async (workspaceContext) => {
    await assertAccess(workspaceContext, "orders.read");

    const backendResponse = await fetch(
      `${serverEnv.BACKEND_API_URL}/work-orders/${context.params.workOrderId}/document?format=${encodeURIComponent(format)}&locale=${encodeURIComponent(locale)}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${workspaceContext.accessToken}`,
          "X-Workspace-Id": workspaceContext.workspaceId,
          Accept: resolveAccept(format),
          "Accept-Language": locale,
          ...(workspaceContext.forwardedFor ? { "X-Forwarded-For": workspaceContext.forwardedFor } : {})
        },
        cache: "no-store"
      }
    );

    if (!backendResponse.ok) {
      let message = "Document generation failed";
      try {
        const payload = (await backendResponse.json()) as { message?: string; error?: { message?: string } };
        message = payload?.error?.message ?? payload?.message ?? message;
      } catch {
        // Keep default message.
      }
      return NextResponse.json({ message }, { status: backendResponse.status });
    }

    const content = await backendResponse.arrayBuffer();
    const contentType = backendResponse.headers.get("content-type") ?? resolveAccept(format);
    const disposition =
      backendResponse.headers.get("content-disposition") ??
      `attachment; filename="work-order-${context.params.workOrderId}.${format}"`;

    return new NextResponse(content, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": disposition,
        "Cache-Control": "no-store"
      }
    });
  });

  if ("status" in result) {
    return result;
  }
  return result.data;
}
