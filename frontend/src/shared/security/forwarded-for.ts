export function resolveForwardedFor(request: Request): string | undefined {
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) {
    const first = forwardedFor.split(",")[0]?.trim();
    if (first) {
      return first;
    }
  }

  const realIp = request.headers.get("x-real-ip");
  if (realIp) {
    return realIp.trim() || undefined;
  }

  return undefined;
}
