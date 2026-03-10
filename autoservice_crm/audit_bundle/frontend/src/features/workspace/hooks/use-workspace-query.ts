"use client";

import { useEffect } from "react";
import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { useAuthStore } from "@/features/auth/model/auth-store";
import type { WorkspaceListResponse } from "@/features/auth/types/auth-types";
import { fetchWorkspaces, workspaceAccessQueryKeys } from "@/features/workspace/api";
import { useWorkspaceStore } from "@/features/workspace/model/workspace-store";
import type { ApiClientError } from "@/shared/api/client";

export function useWorkspaceQuery(): UseQueryResult<WorkspaceListResponse, ApiClientError> {
  const authStatus = useAuthStore((state) => state.status);
  const authSession = useAuthStore((state) => state.session);
  const setActiveWorkspaceId = useWorkspaceStore((state) => state.setActiveWorkspaceId);

  const query = useQuery<WorkspaceListResponse, ApiClientError>({
    queryKey: workspaceAccessQueryKeys.list,
    queryFn: fetchWorkspaces,
    staleTime: 30_000,
    enabled: authStatus === "authenticated"
  });

  useEffect(() => {
    if (query.data?.activeWorkspaceId) {
      setActiveWorkspaceId(query.data.activeWorkspaceId);
      return;
    }

    if (authSession?.workspaceId) {
      setActiveWorkspaceId(authSession.workspaceId);
    }
  }, [authSession?.workspaceId, query.data?.activeWorkspaceId, setActiveWorkspaceId]);

  return query;
}

