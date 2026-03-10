import { useQuery } from "@tanstack/react-query";

import { fetchToday, workspaceQueryKeys } from "@/features/workspace/api";
import type { TodayView } from "@/features/workspace/types";
import type { ApiClientError } from "@/shared/api/client";

export function useWorkspaceTodayQuery() {
  return useQuery<TodayView, ApiClientError>({
    queryKey: workspaceQueryKeys.today,
    queryFn: fetchToday
  });
}
