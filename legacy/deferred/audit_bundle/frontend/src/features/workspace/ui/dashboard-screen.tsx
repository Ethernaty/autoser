"use client";

import Link from "next/link";
import { Clock3, ClipboardList, PlusSquare, Wallet } from "lucide-react";

import { ROUTES } from "@/core/config/routes";
import { Button } from "@/design-system/primitives/button";
import { Card } from "@/design-system/primitives/card";
import { DataTable } from "@/design-system/primitives/data-table/data-table";
import type { DataTableColumn } from "@/design-system/primitives/data-table/data-table.types";
import { Badge } from "@/design-system/primitives/badge";
import { PageLayout, Section, StateBoundary, Toolbar } from "@/design-system/patterns";
import { DisableIfNoAccess } from "@/features/access/ui/access-guard";
import { useChangeOrderStatusMutation, useWorkspaceDashboardQuery } from "@/features/workspace/hooks";
import { OrderStatusBadge } from "@/features/workspace/ui/order-status-badge";
import type { WorkspaceOrderCard } from "@/features/workspace/types";

function KpiCard({ label, value }: { label: string; value: number }): JSX.Element {
  return (
    <Card className="border-neutral-200 p-3">
      <p className="text-sm text-neutral-600">{label}</p>
      <p className="mt-1 text-[24px] leading-[32px] font-semibold text-neutral-900">{value}</p>
    </Card>
  );
}

export function DashboardScreen(): JSX.Element {
  const dashboardQuery = useWorkspaceDashboardQuery();
  const statusMutation = useChangeOrderStatusMutation();

  const columns: DataTableColumn<WorkspaceOrderCard>[] = [
    {
      id: "client",
      header: "Client",
      minWidth: 180,
      cell: (row) => <span className="font-medium text-neutral-900">{row.clientName}</span>
    },
    {
      id: "description",
      header: "Order",
      minWidth: 280,
      cell: (row) => <span className="line-clamp-1">{row.description}</span>
    },
    {
      id: "status",
      header: "Status",
      minWidth: 140,
      cell: (row) => <OrderStatusBadge status={row.status} />
    },
    {
      id: "price",
      header: "Amount",
      minWidth: 120,
      align: "right",
      cell: (row) => row.price
    },
    {
      id: "time",
      header: "Created",
      minWidth: 180,
      align: "right",
      cell: (row) => new Date(row.createdAt).toLocaleString()
    }
  ];

  return (
    <PageLayout title="Dashboard" subtitle={dashboardQuery.data?.nowLabel ?? "Loading..."}>
      <Section>
        <Toolbar
          trailing={
            <div className="flex flex-wrap items-center gap-1">
              <DisableIfNoAccess permission="orders.create" limitType="maxOrdersPerMonth">
                {(disabled, onUpgrade) => (
                  <>
                    <Link href={ROUTES.newOrder}>
                      <Button variant="primary" disabled={disabled}>
                        <PlusSquare className="h-2.5 w-2.5" />
                        New order
                      </Button>
                    </Link>
                    {disabled ? (
                      <Button variant="secondary" onClick={onUpgrade}>
                        Upgrade
                      </Button>
                    ) : null}
                  </>
                )}
              </DisableIfNoAccess>
              <Link href={ROUTES.orders}>
                <Button variant="secondary">
                  <ClipboardList className="h-2.5 w-2.5" />
                  Orders
                </Button>
              </Link>
              <Link href={ROUTES.today}>
                <Button variant="secondary">
                  <Clock3 className="h-2.5 w-2.5" />
                  Today
                </Button>
              </Link>
              <Link href={ROUTES.cashDesk}>
                <Button variant="secondary">
                  <Wallet className="h-2.5 w-2.5" />
                  Cash desk
                </Button>
              </Link>
            </div>
          }
        >
          <Badge tone="neutral">Operations center</Badge>
        </Toolbar>
      </Section>

      <StateBoundary loading={dashboardQuery.isLoading} error={dashboardQuery.error?.message} skeleton="page">
        {dashboardQuery.data ? (
          <>
            <section className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-4">
              <KpiCard label="In progress" value={dashboardQuery.data.inProgressCount} />
              <KpiCard label="Waiting" value={dashboardQuery.data.waitingCount} />
              <KpiCard label="Ready" value={dashboardQuery.data.readyCount} />
              <KpiCard label="Cash queue" value={dashboardQuery.data.cashCount} />
            </section>

            <Section title="Recent orders" description="Quick actions without leaving dashboard">
              <DataTable
                columns={columns}
                rows={dashboardQuery.data.recentOrders}
                getRowId={(row) => row.id}
                emptyTitle="No recent orders"
                emptyDescription="Create an order to see it in this feed."
                rowActions={[
                  {
                    id: "start",
                    label: "Start",
                    onClick: (row) => statusMutation.mutate({ orderId: row.id, status: "in_progress" }),
                    hidden: (row) => row.status !== "new",
                    disabled: () => statusMutation.isPending
                  },
                  {
                    id: "ready",
                    label: "Ready",
                    onClick: (row) => statusMutation.mutate({ orderId: row.id, status: "completed" }),
                    hidden: (row) => row.status !== "in_progress",
                    disabled: () => statusMutation.isPending
                  }
                ]}
              />
            </Section>
          </>
        ) : null}
      </StateBoundary>
    </PageLayout>
  );
}
