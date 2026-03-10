import { useQuery } from "@tanstack/react-query";

import { searchClients, workspaceQueryKeys } from "@/features/workspace/api";
import type { ClientRecord } from "@/features/workspace/types";
import type { ApiClientError } from "@/shared/api/client";

export function useWorkspaceClientSearchQuery(query: string) {
  const normalized = query.trim();

  return useQuery<{ items: ClientRecord[] }, ApiClientError>({
    queryKey: workspaceQueryKeys.clientsSearch(normalized),
    queryFn: async () => {
      const response = await searchClients(normalized, 8);
      return { items: response.items };
    },
    enabled: normalized.length >= 2
  });
}

