import { useQuery } from "@tanstack/react-query";

import { fetchOrders, workspaceQueryKeys } from "@/features/workspace/api";
import type { OrderRecord, PagedResponse } from "@/features/workspace/types";
import type { ApiClientError } from "@/shared/api/client";

export function useWorkspaceOrdersQuery(params: { q?: string; limit?: number; offset?: number }) {
  const q = params.q?.trim() ?? "";
  const limit = params.limit ?? 20;
  const offset = params.offset ?? 0;

  return useQuery<PagedResponse<OrderRecord>, ApiClientError>({
    queryKey: workspaceQueryKeys.ordersList(q, limit, offset),
    queryFn: () => fetchOrders({ q, limit, offset })
  });
}

