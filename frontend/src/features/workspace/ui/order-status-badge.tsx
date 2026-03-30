"use client";

import { StatusIndicator } from "@/design-system/primitives/status-indicator";
import { useI18n } from "@/shared/i18n";

type OrderStatusValue =
  | "new"
  | "in_progress"
  | "completed"
  | "canceled"
  | "completed_unpaid"
  | "completed_paid"
  | "cancelled";

export function OrderStatusBadge({ status }: { status: OrderStatusValue }): JSX.Element {
  const { t } = useI18n();

  if (status === "in_progress" || status === "completed_unpaid") {
    return <StatusIndicator status="degraded" label={t("dashboard.status.in_progress")} />;
  }

  if (status === "completed_paid" || status === "completed") {
    return <StatusIndicator status="online" label={t("dashboard.status.completed_paid")} />;
  }

  if (status === "cancelled" || status === "canceled") {
    return <StatusIndicator status="offline" label={t("dashboard.status.cancelled")} />;
  }

  return <StatusIndicator status="paused" label={t("dashboard.status.new")} />;
}
