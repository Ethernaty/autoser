"use client";

import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { authQueryKeys, me } from "@/features/auth/api/auth-api";
import type { AuthSession } from "@/features/auth/types/auth-types";
import type { ApiClientError } from "@/shared/api/client";

export function useSessionQuery(): UseQueryResult<AuthSession, ApiClientError> {
  return useQuery<AuthSession, ApiClientError>({
    queryKey: authQueryKeys.session,
    queryFn: me,
    staleTime: 60_000,
    retry: false
  });
}
