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

function isLoopbackHost(hostname: string): boolean {
  return hostname === "127.0.0.1" || hostname === "localhost";
}

function isDevLoopbackMatch(origin: string, expectedOrigin: string): boolean {
  if (process.env.NODE_ENV === "production") {
    return false;
  }

  try {
    const actual = new URL(origin);
    const expected = new URL(expectedOrigin);
    return (
      actual.protocol === expected.protocol &&
      actual.port === expected.port &&
      isLoopbackHost(actual.hostname) &&
      isLoopbackHost(expected.hostname)
    );
  } catch {
    return false;
  }
}

export function enforceSameOrigin(request: Request): NextResponse | null {
  const origin = resolveOrigin(request);
  if (!origin) {
    return NextResponse.json({ message: "Origin header is required" }, { status: 403 });
  }

  const expected = new URL(request.url).origin;
  if (origin !== expected && !isDevLoopbackMatch(origin, expected)) {
    return NextResponse.json({ message: "Invalid request origin" }, { status: 403 });
  }

  return null;
}
