import { QueryCache, MutationCache, QueryClient } from "@tanstack/react-query";

import { ApiClientError } from "@/shared/api/client";

function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiClientError) {
    if (error.status >= 500) {
      return failureCount < 2;
    }

    return false;
  }

  return failureCount < 1;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: () => {
        // Global query error hook.
      }
    }),
    mutationCache: new MutationCache({
      onError: () => {
        // Global mutation error hook.
      }
    }),
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        gcTime: 5 * 60_000,
        retry: shouldRetry,
        refetchOnWindowFocus: false,
        throwOnError: (error) => error instanceof ApiClientError && error.status >= 500
      },
      mutations: {
        retry: shouldRetry,
        throwOnError: (error) => error instanceof ApiClientError && error.status >= 500
      }
    }
  });
}
