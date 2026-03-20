import { apiClient } from "@/shared/api/client";
import type { AuthSession, WorkspaceListResponse } from "@/features/auth/types/auth-types";

export const workspaceAccessQueryKeys = {
  list: ["workspaces", "list"] as const
};

export async function fetchWorkspaces(): Promise<WorkspaceListResponse> {
  const response = await apiClient.get<WorkspaceListResponse>("/api/workspaces");
  return response.data;
}

export async function switchWorkspace(workspaceId: string): Promise<AuthSession> {
  const response = await apiClient.post<AuthSession>("/api/workspaces/switch", {
    workspaceId
  });

  return response.data;
}

