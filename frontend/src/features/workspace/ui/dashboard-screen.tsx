"use client";

import Link from "next/link";
import type { Route } from "next";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import { Badge, Button, Card } from "@/design-system/primitives";
import { PageLayout, Section, StateBoundary } from "@/design-system/patterns";
import { fetchClients, fetchDashboardSummary, fetchVehicles, fetchWorkOrders, mvpQueryKeys } from "@/features/workspace/api/mvp-api";
import type { WorkOrderRecord, WorkOrderStatus } from "@/features/workspace/types/mvp-types";

function formatCurrency(value: string): string {
  const normalized = Number(value);
  if (!Number.isFinite(normalized)) {
    return value;
  }
  return normalized.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

function statusTone(status: WorkOrderStatus): "neutral" | "warning" | "success" | "error" {
  if (status === "in_progress" || status === "completed_unpaid") {
    return "warning";
  }
  if (status === "completed_paid") {
    return "success";
  }
  if (status === "cancelled") {
    return "error";
  }
  return "neutral";
}

function statusLabel(status: WorkOrderStatus): string {
  if (status === "in_progress") {
    return "In progress";
  }
  if (status === "completed_unpaid") {
    return "Completed (unpaid)";
  }
  if (status === "completed_paid") {
    return "Completed (paid)";
  }
  if (status === "cancelled") {
    return "Cancelled";
  }
  return "New";
}

function KpiCard({
  title,
  value,
  context,
  actionLabel,
  actionHref
}: {
  title: string;
  value: string | number;
  context: string;
  actionLabel: string;
  actionHref: string;
}): JSX.Element {
  return (
    <Card className="border-neutral-200 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</p>
      <p className="mt-1 text-2xl font-semibold text-neutral-900 tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-neutral-600">{context}</p>
      <div className="mt-3">
        <Link href={actionHref as Route}>
          <Button size="sm" variant="secondary">
            {actionLabel}
          </Button>
        </Link>
      </div>
    </Card>
  );
}

export function DashboardScreen(): JSX.Element {
  const today = new Date().toLocaleDateString();

  const summaryQuery = useQuery({
    queryKey: mvpQueryKeys.dashboardSummary,
    queryFn: () => fetchDashboardSummary(6)
  });

  const workOrdersQuery = useQuery({
    queryKey: mvpQueryKeys.workOrders("", 40, 0),
    queryFn: () => fetchWorkOrders({ q: "", limit: 40, offset: 0 })
  });

  const clientsQuery = useQuery({
    queryKey: mvpQueryKeys.clients("", 200, 0),
    queryFn: () => fetchClients({ q: "", limit: 200, offset: 0 })
  });

  const vehiclesQuery = useQuery({
    queryKey: mvpQueryKeys.vehicles("", "", 250, 0),
    queryFn: () => fetchVehicles({ q: "", limit: 250, offset: 0 })
  });

  const clientsById = useMemo(() => {
    const map = new Map<string, string>();
    (clientsQuery.data?.items ?? []).forEach((client) => map.set(client.id, client.name));
    return map;
  }, [clientsQuery.data?.items]);

  const vehiclesById = useMemo(() => {
    const map = new Map<string, string>();
    (vehiclesQuery.data?.items ?? []).forEach((vehicle) => map.set(vehicle.id, `${vehicle.plate_number} - ${vehicle.make_model}`));
    return map;
  }, [vehiclesQuery.data?.items]);

  const activeWorkOrders = useMemo<WorkOrderRecord[]>(() => {
    const rows = workOrdersQuery.data?.items ?? [];
    return rows.filter((row) => row.status === "new" || row.status === "in_progress").slice(0, 8);
  }, [workOrdersQuery.data?.items]);

  return (
    <PageLayout title="Dashboard" subtitle="What is happening now and what to do next">
      <Section title="Quick actions" description="Start the most common daily operations.">
        <div className="flex flex-wrap gap-2">
          <Link href={ROUTES.workOrderNew as Route}>
            <Button variant="primary">Create work order</Button>
          </Link>
          <Link href={ROUTES.clients as Route}>
            <Button variant="secondary">Add client</Button>
          </Link>
          <Link href={ROUTES.vehicles as Route}>
            <Button variant="secondary">Add vehicle</Button>
          </Link>
        </div>
      </Section>

      <StateBoundary loading={summaryQuery.isLoading} error={summaryQuery.error?.message}>
        {summaryQuery.data ? (
          <section className="grid grid-cols-1 gap-2 md:grid-cols-3">
            <KpiCard
              title="Open queue"
              value={summaryQuery.data.open_work_orders_count}
              context={`Today: ${today}. Needs operator attention.`}
              actionLabel="Open queue"
              actionHref={ROUTES.workOrders}
            />
            <KpiCard
              title="Closed orders"
              value={summaryQuery.data.closed_work_orders_count}
              context={`Today: ${today}. Completed and closed.`}
              actionLabel="Review orders"
              actionHref={ROUTES.workOrders}
            />
            <KpiCard
              title="Revenue total"
              value={formatCurrency(summaryQuery.data.revenue_total)}
              context={`Status: updated from recorded payments.`}
              actionLabel="Go to work orders"
              actionHref={ROUTES.workOrders}
            />
          </section>
        ) : null}
      </StateBoundary>

      <Section
        title="Active work orders"
        description="Current operational queue with core details for quick dispatch and cash control."
        actions={
          <Link href={ROUTES.workOrders as Route}>
            <Button variant="secondary">All work orders</Button>
          </Link>
        }
      >
        {workOrdersQuery.isLoading ? (
          <p className="text-sm text-neutral-600">Loading active queue...</p>
        ) : workOrdersQuery.error ? (
          <p className="text-sm text-error">{workOrdersQuery.error.message}</p>
        ) : activeWorkOrders.length ? (
          <div className="space-y-1.5">
            {activeWorkOrders.map((order) => (
              <div
                key={order.id}
                className="grid grid-cols-1 gap-2 rounded-md border border-neutral-200 bg-neutral-50 p-3 lg:grid-cols-[minmax(0,1fr)_auto_auto]"
              >
                <div className="min-w-0">
                  <Link href={ROUTES.workOrderDetail(order.id) as Route} className="truncate text-sm font-semibold text-primary hover:underline">
                    {order.description || `Work order #${order.id.slice(0, 8)}`}
                  </Link>
                  <p className="mt-1 truncate text-xs text-neutral-600">
                    {clientsById.get(order.client_id) ?? order.client_id} |{" "}
                    {order.vehicle_id ? vehiclesById.get(order.vehicle_id) ?? order.vehicle_id : "No vehicle linked"}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Badge tone={statusTone(order.status)}>{statusLabel(order.status)}</Badge>
                </div>

                <div className="text-left lg:text-right">
                  <p className="text-xs text-neutral-500">Total amount</p>
                  <p className="text-sm font-semibold tabular-nums text-neutral-900">{formatCurrency(order.total_amount)}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-md border border-dashed border-neutral-300 bg-neutral-50 p-4">
            <p className="text-sm font-medium text-neutral-800">No active work orders right now.</p>
            <p className="mt-1 text-sm text-neutral-600">Start with your first work order to launch the daily queue.</p>
            <div className="mt-3">
              <Link href={ROUTES.workOrderNew as Route}>
                <Button variant="primary">Create work order</Button>
              </Link>
            </div>
          </div>
        )}
      </Section>

      {summaryQuery.data?.recent_activity?.length ? (
        <Section title="Recent activity" description="Latest important changes in your workspace.">
          <div className="space-y-1">
            {summaryQuery.data.recent_activity.map((item) => (
              <div key={item.id} className="rounded-sm border border-neutral-200 p-2">
                <div className="flex flex-wrap items-start justify-between gap-1">
                  <p className="text-sm font-medium text-neutral-900">
                    {item.entity} - {item.action}
                  </p>
                  <p className="text-xs text-neutral-500">{new Date(item.created_at).toLocaleString()}</p>
                </div>
              </div>
            ))}
          </div>
        </Section>
      ) : null}
    </PageLayout>
  );
}
