import type { QueryClient } from "@tanstack/react-query";

export async function resetWorkspaceBoundCache(queryClient: QueryClient): Promise<void> {
  await queryClient.cancelQueries();

  queryClient.removeQueries({
    predicate: (query) => {
      const root = Array.isArray(query.queryKey) ? query.queryKey[0] : null;
      return root !== "auth";
    }
  });
}

