import { NextResponse } from "next/server";

function resolveOrigin(request: Request): string | null {
  const origin = request.headers.get("origin");
  if (origin) {
    return origin;
  }

  const referer = request.headers.get("referer");
  if (!referer) {
    return null;
  }

  try {
    return new URL(referer).origin;
  } catch {
    return null;
  }
}

export function enforceSameOrigin(request: Request): NextResponse | null {
  const origin = resolveOrigin(request);
  if (!origin) {
    return NextResponse.json({ message: "Origin header is required" }, { status: 403 });
  }

  const expected = new URL(request.url).origin;
  if (origin !== expected) {
    return NextResponse.json({ message: "Invalid request origin" }, { status: 403 });
  }

  return null;
}
