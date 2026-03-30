"use client";

import { ErrorState } from "@/shared/ui/error-state";
import { EmptyState } from "@/shared/ui/empty-state";
import { useI18n } from "@/shared/i18n";
import { SkeletonState } from "@/shared/ui/skeleton-state";

type StateBoundaryProps = {
  loading?: boolean;
  skeleton?: "page" | "section" | "table";
  empty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  error?: string | null;
  onRetry?: () => void;
  children: React.ReactNode;
};

export function StateBoundary({
  loading,
  skeleton = "section",
  empty,
  emptyTitle,
  emptyDescription,
  error,
  onRetry,
  children
}: StateBoundaryProps): JSX.Element {
  const { t } = useI18n();
  const resolvedEmptyTitle = emptyTitle ?? t("state.empty.title");
  const resolvedEmptyDescription = emptyDescription ?? t("state.empty.description");

  if (loading) {
    return <SkeletonState variant={skeleton} />;
  }

  if (error) {
    return <ErrorState title={t("state.error.title")} description={error} onRetry={onRetry} />;
  }

  if (empty) {
    return <EmptyState title={resolvedEmptyTitle} description={resolvedEmptyDescription} />;
  }

  return <>{children}</>;
}
