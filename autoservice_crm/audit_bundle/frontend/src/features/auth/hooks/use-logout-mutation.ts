"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { Route } from "next";
import { useRouter } from "next/navigation";

import { ROUTES } from "@/core/config/routes";
import { authQueryKeys, logout } from "@/features/auth/api/auth-api";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { resetWorkspaceBoundCache } from "@/features/workspace/model/workspace-query-reset";
import { useWorkspaceStore } from "@/features/workspace/model/workspace-store";
import type { ApiClientError } from "@/shared/api/client";

export function useLogoutMutation() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const clearSession = useAuthStore((state) => state.clearSession);
  const clearActiveWorkspace = useWorkspaceStore((state) => state.clearActiveWorkspace);

  return useMutation({
    mutationFn: logout,
    onSettled: async () => {
      clearSession();
      clearActiveWorkspace();

      await resetWorkspaceBoundCache(queryClient);
      await queryClient.cancelQueries({ queryKey: authQueryKeys.session });
      queryClient.removeQueries({ queryKey: authQueryKeys.session });

      router.replace(ROUTES.login as Route);
    }
  }) as ReturnType<typeof useMutation<void, ApiClientError, void>>;
}

