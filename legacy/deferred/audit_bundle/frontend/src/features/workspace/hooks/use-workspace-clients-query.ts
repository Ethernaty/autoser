import { useQuery } from "@tanstack/react-query";

import { fetchClients, workspaceQueryKeys } from "@/features/workspace/api";
import type { ClientRecord, PagedResponse } from "@/features/workspace/types";
import type { ApiClientError } from "@/shared/api/client";

export function useWorkspaceClientsQuery(params: { q?: string; limit?: number; offset?: number }) {
  const q = params.q?.trim() ?? "";
  const limit = params.limit ?? 20;
  const offset = params.offset ?? 0;

  return useQuery<PagedResponse<ClientRecord>, ApiClientError>({
    queryKey: workspaceQueryKeys.clientsList(q, limit, offset),
    queryFn: () => fetchClients({ q, limit, offset })
  });
}

