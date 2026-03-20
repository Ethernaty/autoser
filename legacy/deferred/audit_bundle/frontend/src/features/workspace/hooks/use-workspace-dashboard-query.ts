import { useQuery } from "@tanstack/react-query";

import { fetchDashboard, workspaceQueryKeys } from "@/features/workspace/api";
import type { DashboardView } from "@/features/workspace/types";
import type { ApiClientError } from "@/shared/api/client";

export function useWorkspaceDashboardQuery() {
  return useQuery<DashboardView, ApiClientError>({
    queryKey: workspaceQueryKeys.dashboard,
    queryFn: fetchDashboard
  });
}
