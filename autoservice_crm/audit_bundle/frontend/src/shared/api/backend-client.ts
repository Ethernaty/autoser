import "server-only";

import { serverEnv } from "@/core/config/server-env";

export class BackendApiError extends Error {
  readonly status: number;
  readonly payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "BackendApiError";
    this.status = status;
    this.payload = payload;
  }
}

export async function backendRequest<TResponse>(
  path: string,
  options: RequestInit = {}
): Promise<TResponse> {
  const timeoutMs = Number.parseInt(process.env.BACKEND_TIMEOUT_MS ?? "15000", 10);
  const controller = new AbortController();
  const timeout = Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 15000;
  const timer = setTimeout(() => controller.abort(), timeout);

  let response: Response;
  try {
    response = await fetch(`${serverEnv.BACKEND_API_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(options.headers ?? {})
      },
      cache: "no-store",
      signal: controller.signal
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new BackendApiError("Backend request timed out", 504, { code: "backend_timeout" });
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }

  const data = await response
    .json()
    .catch(() => null);

  if (!response.ok) {
    const message =
      (data && typeof data === "object" && "detail" in data && typeof data.detail === "string" && data.detail) ||
      (data && typeof data === "object" && "message" in data && typeof data.message === "string" && data.message) ||
      "Backend request failed";

    throw new BackendApiError(message, response.status, data);
  }

  return data as TResponse;
}
