"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { authQueryKeys, login } from "@/features/auth/api/auth-api";
import { useAuthStore } from "@/features/auth/model/auth-store";
import type { LoginPayload } from "@/features/auth/types/auth-types";
import { useWorkspaceStore } from "@/features/workspace/model/workspace-store";
import type { ApiClientError } from "@/shared/api/client";

export function useLoginMutation() {
  const queryClient = useQueryClient();
  const setSession = useAuthStore((state) => state.setSession);
  const setUnauthenticated = useAuthStore((state) => state.setUnauthenticated);
  const setActiveWorkspaceId = useWorkspaceStore((state) => state.setActiveWorkspaceId);
  const clearActiveWorkspace = useWorkspaceStore((state) => state.clearActiveWorkspace);

  return useMutation({
    mutationFn: (payload: LoginPayload) => login(payload),
    onSuccess: (session) => {
      setSession(session);
      setActiveWorkspaceId(session.workspaceId);
      queryClient.setQueryData(authQueryKeys.session, session);
    },
    onError: () => {
      setUnauthenticated();
      clearActiveWorkspace();
    }
  }) as ReturnType<typeof useMutation<Awaited<ReturnType<typeof login>>, ApiClientError, LoginPayload>>;
}

