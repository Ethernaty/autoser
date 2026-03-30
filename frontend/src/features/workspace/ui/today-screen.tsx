"use client";

import { Card } from "@/design-system/primitives/card";
import { Button } from "@/design-system/primitives/button";
import { PageLayout, StateBoundary } from "@/design-system/patterns";
import { DisableIfNoAccess } from "@/features/access/ui/access-guard";
import { useChangeOrderStatusMutation, useWorkspaceTodayQuery } from "@/features/workspace/hooks";
import { OrderStatusBadge } from "@/features/workspace/ui/order-status-badge";
import { useI18n } from "@/shared/i18n";

function OrderList({
  title,
  items,
  action
}: {
  title: string;
  items: Array<{
    id: string;
    clientName: string;
    description: string;
    createdAt: string;
    status: "new" | "in_progress" | "completed" | "canceled";
    overdue: boolean;
  }>;
  action?: {
    label: string;
    nextStatus: "new" | "in_progress" | "completed" | "canceled";
  };
}): JSX.Element {
  const statusMutation = useChangeOrderStatusMutation();
  const { t } = useI18n();

  return (
    <Card className="space-y-2 p-3">
      <h2 className="text-lg font-semibold text-neutral-900">{title}</h2>
      {items.length ? (
        <div className="space-y-1">
          {items.map((item) => (
            <div key={item.id} className="rounded-md border border-neutral-200 p-2">
              <div className="flex flex-wrap items-start justify-between gap-1">
                <div>
                  <p className="text-sm font-semibold text-neutral-900">{item.clientName}</p>
                  <p className="text-sm text-neutral-600">{item.description}</p>
                  <p className="text-xs text-neutral-500">{new Date(item.createdAt).toLocaleString()}</p>
                </div>
                <OrderStatusBadge status={item.status} />
              </div>
              {action ? (
                <div className="mt-2">
                  <DisableIfNoAccess permission="orders.change_status">
                    {(disabled) => (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={disabled}
                        onClick={() => statusMutation.mutate({ orderId: item.id, status: action.nextStatus })}
                      >
                        {action.label}
                      </Button>
                    )}
                  </DisableIfNoAccess>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-neutral-600">{t("today.empty")}</p>
      )}
    </Card>
  );
}

export function TodayScreen(): JSX.Element {
  const todayQuery = useWorkspaceTodayQuery();
  const { t } = useI18n();

  return (
    <PageLayout title={t("today.title")} subtitle={todayQuery.data?.nowLabel ?? t("common.loading")}>
      <StateBoundary loading={todayQuery.isLoading} error={todayQuery.error?.message}>
        {todayQuery.data ? (
          <div className="grid grid-cols-1 gap-2 xl:grid-cols-2">
            <OrderList
              title={t("today.in_progress")}
              items={todayQuery.data.inProgress}
              action={{ label: t("today.mark_ready"), nextStatus: "completed" }}
            />
            <OrderList title={t("today.waiting")} items={todayQuery.data.waiting} action={{ label: t("today.start"), nextStatus: "in_progress" }} />
            <OrderList title={t("today.overdue")} items={todayQuery.data.overdue} action={{ label: t("today.start"), nextStatus: "in_progress" }} />
            <OrderList title={t("today.ready")} items={todayQuery.data.ready} />
          </div>
        ) : null}
      </StateBoundary>
    </PageLayout>
  );
}
