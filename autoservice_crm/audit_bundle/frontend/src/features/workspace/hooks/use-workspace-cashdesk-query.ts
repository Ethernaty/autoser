import { useQuery } from "@tanstack/react-query";

import { fetchCashDesk, workspaceQueryKeys } from "@/features/workspace/api";
import type { CashDeskView } from "@/features/workspace/types";
import type { ApiClientError } from "@/shared/api/client";

export function useWorkspaceCashDeskQuery() {
  return useQuery<CashDeskView, ApiClientError>({
    queryKey: workspaceQueryKeys.cashDesk,
    queryFn: fetchCashDesk
  });
}
