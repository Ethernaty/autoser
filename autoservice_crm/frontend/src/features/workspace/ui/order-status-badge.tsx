import { StatusIndicator } from "@/design-system/primitives/status-indicator";
import type { OrderStatus } from "@/features/workspace/types";

export function OrderStatusBadge({ status }: { status: OrderStatus }): JSX.Element {
  if (status === "in_progress") {
    return <StatusIndicator status="degraded" label="In progress" />;
  }

  if (status === "completed") {
    return <StatusIndicator status="online" label="Completed" />;
  }

  if (status === "canceled") {
    return <StatusIndicator status="offline" label="Canceled" />;
  }

  return <StatusIndicator status="paused" label="New" />;
}
