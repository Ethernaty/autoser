"use client";

import { QueryClientProvider, QueryErrorResetBoundary } from "@tanstack/react-query";
import { type PropsWithChildren, useState } from "react";
import { ErrorBoundary } from "react-error-boundary";

import { createQueryClient } from "@/core/lib/query-client";
import { ErrorState } from "@/shared/ui/error-state";

export function QueryProvider({ children }: PropsWithChildren): JSX.Element {
  const [queryClient] = useState(() => createQueryClient());

  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <ErrorBoundary
          onReset={reset}
          fallbackRender={({ error, resetErrorBoundary }) => (
            <div className="mx-auto w-full max-w-content p-4">
              <ErrorState title="Unhandled application error" description={error.message} onRetry={resetErrorBoundary} />
            </div>
          )}
        >
          <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
        </ErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  );
}
