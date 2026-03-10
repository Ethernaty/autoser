"use client";

import { useEffect } from "react";

import { useSessionQuery } from "@/features/auth/hooks/use-session-query";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { useWorkspaceStore } from "@/features/workspace/model/workspace-store";
import { subscribeUnauthorized } from "@/shared/api/events";

export function AuthBootstrap({ children }: { children: React.ReactNode }): JSX.Element {
  const setLoading = useAuthStore((state) => state.setLoading);
  const setSession = useAuthStore((state) => state.setSession);
  const setUnauthenticated = useAuthStore((state) => state.setUnauthenticated);
  const setActiveWorkspaceId = useWorkspaceStore((state) => state.setActiveWorkspaceId);
  const clearActiveWorkspace = useWorkspaceStore((state) => state.clearActiveWorkspace);

  const sessionQuery = useSessionQuery();

  useEffect(() => {
    const unsubscribe = subscribeUnauthorized(() => {
      setUnauthenticated();
      clearActiveWorkspace();
    });

    return unsubscribe;
  }, [clearActiveWorkspace, setUnauthenticated]);

  useEffect(() => {
    if (sessionQuery.isPending) {
      setLoading();
      return;
    }

    if (sessionQuery.isSuccess) {
      setSession(sessionQuery.data);
      setActiveWorkspaceId(sessionQuery.data.workspaceId);
      return;
    }

    if (sessionQuery.isError) {
      setUnauthenticated();
      clearActiveWorkspace();
    }
  }, [
    clearActiveWorkspace,
    sessionQuery.data,
    sessionQuery.isError,
    sessionQuery.isPending,
    sessionQuery.isSuccess,
    setActiveWorkspaceId,
    setLoading,
    setSession,
    setUnauthenticated
  ]);

  return <>{children}</>;
}

