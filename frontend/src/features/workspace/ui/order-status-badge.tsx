import { StatusIndicator } from "@/design-system/primitives/status-indicator";

type OrderStatusValue =
  | "new"
  | "in_progress"
  | "completed"
  | "canceled"
  | "completed_unpaid"
  | "completed_paid"
  | "cancelled";

export function OrderStatusBadge({ status }: { status: OrderStatusValue }): JSX.Element {
  if (status === "in_progress" || status === "completed_unpaid") {
    return <StatusIndicator status="degraded" label="In progress" />;
  }

  if (status === "completed_paid" || status === "completed") {
    return <StatusIndicator status="online" label="Completed" />;
  }

  if (status === "cancelled" || status === "canceled") {
    return <StatusIndicator status="offline" label="Cancelled" />;
  }

  return <StatusIndicator status="paused" label="New" />;
}
