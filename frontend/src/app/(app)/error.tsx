"use client";

import { ErrorState } from "@/shared/ui/error-state";
import { useI18n } from "@/shared/i18n";

export default function AppError({ error, reset }: { error: Error; reset: () => void }): JSX.Element {
  const { t } = useI18n();
  return <ErrorState title={t("app.error.title")} description={error.message} onRetry={reset} />;
}
