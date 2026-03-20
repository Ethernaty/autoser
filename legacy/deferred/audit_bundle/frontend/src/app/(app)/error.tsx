"use client";

import { ErrorState } from "@/shared/ui/error-state";

export default function AppError({ error, reset }: { error: Error; reset: () => void }): JSX.Element {
  return <ErrorState title="Something went wrong" description={error.message} onRetry={reset} />;
}
