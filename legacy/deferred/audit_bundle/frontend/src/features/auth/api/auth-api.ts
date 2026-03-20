import { apiClient } from "@/shared/api/client";
import type { AuthSession, LoginPayload } from "@/features/auth/types/auth-types";

export const authQueryKeys = {
  session: ["auth", "session"] as const
};

export async function login(payload: LoginPayload): Promise<AuthSession> {
  const response = await apiClient.post<AuthSession>("/auth/login", {
    email: payload.email,
    password: payload.password,
    tenantSlug: payload.tenantSlug
  }, {
    skipAuthHandling: true
  });
  return response.data;
}

export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout", undefined, {
    skipAuthHandling: true
  });
}

export async function me(): Promise<AuthSession> {
  const response = await apiClient.get<AuthSession>("/auth/me", {
    skipAuthHandling: true
  });
  return response.data;
}
