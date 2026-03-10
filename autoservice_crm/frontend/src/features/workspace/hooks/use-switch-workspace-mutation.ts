"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { authQueryKeys } from "@/features/auth/api/auth-api";
import { useAuthStore } from "@/features/auth/model/auth-store";
import type { AuthSession } from "@/features/auth/types/auth-types";
import { switchWorkspace, workspaceAccessQueryKeys } from "@/features/workspace/api";
import { resetWorkspaceBoundCache } from "@/features/workspace/model/workspace-query-reset";
import { useWorkspaceStore } from "@/features/workspace/model/workspace-store";
import type { ApiClientError } from "@/shared/api/client";

export function useSwitchWorkspaceMutation() {
  const queryClient = useQueryClient();
  const setSession = useAuthStore((state) => state.setSession);
  const setActiveWorkspaceId = useWorkspaceStore((state) => state.setActiveWorkspaceId);

  return useMutation<AuthSession, ApiClientError, { workspaceId: string }>({
    mutationFn: ({ workspaceId }) => switchWorkspace(workspaceId),
    onSuccess: async (session) => {
      await resetWorkspaceBoundCache(queryClient);

      setSession(session);
      setActiveWorkspaceId(session.workspaceId);

      queryClient.setQueryData(authQueryKeys.session, session);
      void queryClient.invalidateQueries({ queryKey: workspaceAccessQueryKeys.list });
    }
  });
}

