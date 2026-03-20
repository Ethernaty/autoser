import { ErrorState } from "@/shared/ui/error-state";
import { EmptyState } from "@/shared/ui/empty-state";
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
  emptyTitle = "No data",
  emptyDescription,
  error,
  onRetry,
  children
}: StateBoundaryProps): JSX.Element {
  if (loading) {
    return <SkeletonState variant={skeleton} />;
  }

  if (error) {
    return <ErrorState title="Unable to load content" description={error} onRetry={onRetry} />;
  }

  if (empty) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return <>{children}</>;
}
