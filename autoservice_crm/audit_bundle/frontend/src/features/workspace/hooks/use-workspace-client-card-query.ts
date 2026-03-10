import { useQuery } from "@tanstack/react-query";

import { fetchClientCard, workspaceQueryKeys } from "@/features/workspace/api";
import type { ClientCardView } from "@/features/workspace/types";
import type { ApiClientError } from "@/shared/api/client";

export function useWorkspaceClientCardQuery(params: { q?: string; clientId?: string }) {
  const q = params.q ?? "";
  const clientId = params.clientId;

  return useQuery<ClientCardView, ApiClientError>({
    queryKey: workspaceQueryKeys.clientCard(q, clientId),
    queryFn: () => fetchClientCard({ q, clientId }),
    enabled: Boolean(q || clientId)
  });
}
