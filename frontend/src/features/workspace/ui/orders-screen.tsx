"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import { cn } from "@/core/lib/utils";
import { DataTable } from "@/design-system/primitives/data-table/data-table";
import type { DataTableColumn } from "@/design-system/primitives/data-table/data-table.types";
import { Badge, Button, Input, Select } from "@/design-system/primitives";
import { PageLayout } from "@/design-system/patterns";
import {
  closeWorkOrder,
  fetchEmployees,
  fetchWorkOrders,
  mvpQueryKeys,
  setWorkOrderStatus
} from "@/features/workspace/api/mvp-api";
import type { WorkOrderPaymentState, WorkOrderRecord, WorkOrderStatus } from "@/features/workspace/types/mvp-types";
import { useI18n } from "@/shared/i18n";

const PAGE_SIZE = 20;
const LOOKUP_LIMIT = 50;

const STATUS_TONE: Record<WorkOrderStatus, "neutral" | "warning" | "success" | "error"> = {
  new: "neutral",
  in_progress: "warning",
  completed_unpaid: "warning",
  completed_paid: "success",
  cancelled: "error"
};

function formatMoney(value: string): string {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return value;
  }
  return parsed.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function parseMoney(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString();
}

function paymentStateLabel(state: WorkOrderPaymentState, t: (key: string) => string): string {
  if (state === "paid") {
    return t("work_orders.payment_state.paid");
  }
  if (state === "partial") {
    return t("work_orders.payment_state.partial");
  }
  return t("work_orders.payment_state.unpaid");
}

function SummaryMetric({
  label,
  value,
  tone = "neutral",
  emphasized = false
}: {
  label: string;
  value: string | number;
  tone?: "neutral" | "success" | "warning";
  emphasized?: boolean;
}): JSX.Element {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">{label}</p>
      <p
        className={
          "mt-1 truncate font-semibold tabular-nums " +
          (emphasized ? "text-[18px] leading-6 " : "text-[16px] leading-5 ") +
          (tone === "success" ? "text-success" : tone === "warning" ? "text-warning" : "text-neutral-900")
        }
      >
        {value}
      </p>
    </div>
  );
}

export function OrdersScreen(): JSX.Element {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const initialQ = searchParams.get("q") ?? "";
  const initialPageRaw = Number(searchParams.get("page") ?? "1");
  const initialPage = Number.isFinite(initialPageRaw) && initialPageRaw > 0 ? initialPageRaw : 1;
  const initialStatus = (searchParams.get("status") as WorkOrderStatus | null) ?? "all";
  const isInitialStatusValid = initialStatus === "all" || Object.prototype.hasOwnProperty.call(STATUS_TONE, initialStatus);
  const initialAssignee = searchParams.get("assignee") ?? "all";

  const [q, setQ] = useState(initialQ);
  const [search, setSearch] = useState(initialQ);
  const [page, setPage] = useState(initialPage);
  const [statusFilter, setStatusFilter] = useState<"all" | WorkOrderStatus>(isInitialStatusValid ? initialStatus : "all");
  const [assigneeFilter, setAssigneeFilter] = useState<"all" | "unassigned" | string>(initialAssignee);

  useEffect(() => {
    const nextQ = searchParams.get("q") ?? "";
    const nextPageRaw = Number(searchParams.get("page") ?? "1");
    const nextPage = Number.isFinite(nextPageRaw) && nextPageRaw > 0 ? nextPageRaw : 1;
    const nextStatusRaw = (searchParams.get("status") as WorkOrderStatus | null) ?? "all";
    const nextStatus =
      nextStatusRaw === "all" || Object.prototype.hasOwnProperty.call(STATUS_TONE, nextStatusRaw) ? nextStatusRaw : "all";
    const nextAssignee = searchParams.get("assignee") ?? "all";

    setQ(nextQ);
    setSearch(nextQ);
    setPage(nextPage);
    setStatusFilter(nextStatus);
    setAssigneeFilter(nextAssignee);
  }, [searchParams]);

  const updateUrlState = useCallback(
    (next: {
      q: string;
      page: number;
      status: "all" | WorkOrderStatus;
      assignee: "all" | "unassigned" | string;
    }): void => {
      const params = new URLSearchParams(searchParams.toString());

      if (next.q) params.set("q", next.q);
      else params.delete("q");

      if (next.page > 1) params.set("page", String(next.page));
      else params.delete("page");

      if (next.status !== "all") params.set("status", next.status);
      else params.delete("status");

      if (next.assignee !== "all") params.set("assignee", next.assignee);
      else params.delete("assignee");

      const queryString = params.toString();
      const nextHref = queryString ? `${pathname}?${queryString}` : pathname;
      router.replace(nextHref as Route, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      const nextQ = search.trim();
      if (nextQ === q) return;

      setQ(nextQ);
      setPage(1);
      updateUrlState({ q: nextQ, page: 1, status: statusFilter, assignee: assigneeFilter });
    }, 250);

    return () => window.clearTimeout(timeout);
  }, [assigneeFilter, q, search, statusFilter, updateUrlState]);

  const offset = (page - 1) * PAGE_SIZE;
  const workOrdersQuery = useQuery({
    queryKey: mvpQueryKeys.workOrders(q, PAGE_SIZE, offset),
    queryFn: () => fetchWorkOrders({ q, limit: PAGE_SIZE, offset }),
    placeholderData: keepPreviousData
  });

  const employeesQuery = useQuery({
    queryKey: mvpQueryKeys.employees("", "", LOOKUP_LIMIT, 0),
    queryFn: () => fetchEmployees({ limit: LOOKUP_LIMIT, offset: 0 })
  });

  const statusMutation = useMutation({
    mutationFn: ({ workOrderId, status }: { workOrderId: string; status: WorkOrderStatus }) =>
      setWorkOrderStatus(workOrderId, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["work-orders"] });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.dashboardSummary });
    }
  });

  const closeMutation = useMutation({
    mutationFn: (workOrderId: string) => closeWorkOrder(workOrderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["work-orders"] });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.dashboardSummary });
    }
  });

  const employeesById = useMemo(() => {
    const map = new Map<string, string>();
    (employeesQuery.data?.items ?? []).forEach((employee) => map.set(employee.employee_id, employee.email));
    return map;
  }, [employeesQuery.data?.items]);

  const rows = workOrdersQuery.data?.items ?? [];
  const filteredRows = useMemo(() => {
    return rows.filter((row) => {
      const matchesStatus = statusFilter === "all" || row.status === statusFilter;
      const matchesAssignee =
        assigneeFilter === "all" ||
        (assigneeFilter === "unassigned" ? !row.assigned_employee_id : row.assigned_employee_id === assigneeFilter);
      return matchesStatus && matchesAssignee;
    });
  }, [rows, statusFilter, assigneeFilter]);
  const rowNumberById = useMemo(() => {
    const map = new Map<string, number>();
    filteredRows.forEach((row, index) => {
      map.set(row.id, offset + index + 1);
    });
    return map;
  }, [filteredRows, offset]);

  const queueStats = useMemo(() => {
    const openCount = filteredRows.filter((row) => row.status === "new" || row.status === "in_progress").length;
    const completedCount = filteredRows.filter((row) => row.status === "completed_unpaid" || row.status === "completed_paid").length;
    const unassignedCount = filteredRows.filter((row) => !row.assigned_employee_id).length;
    return { openCount, completedCount, unassignedCount };
  }, [filteredRows]);

  const totals = useMemo(() => {
    let totalAmount = 0;
    let paidAmount = 0;
    let remainingAmount = 0;

    filteredRows.forEach((row) => {
      totalAmount += parseMoney(row.total_amount);
      paidAmount += parseMoney(row.paid_amount);
      remainingAmount += parseMoney(row.remaining_amount);
    });

    return { totalAmount, paidAmount, remainingAmount };
  }, [filteredRows]);

  const isRowActionBusy = statusMutation.isPending || closeMutation.isPending;

  const columns = useMemo<DataTableColumn<WorkOrderRecord>[]>(
    () => [
      {
        id: "queue",
        header: t("work_orders.table.queue_item"),
        cell: (row) => (
          <div className="space-y-1">
            <Link href={ROUTES.workOrderDetail(row.id) as Route} className="block truncate font-semibold text-primary hover:underline">
              {row.description}
            </Link>
            <p className="text-xs text-neutral-500">{t("work_orders.created")} {formatDateTime(row.created_at)}</p>
          </div>
        )
      },
      {
        id: "party",
        header: t("work_orders.table.client_vehicle"),
        cell: (row) => {
          const rowNumber = rowNumberById.get(row.id);
          const clientLabel =
            row.client_name?.trim() ||
            `${t("work_orders.client_fallback")} №${rowNumber ?? ""}`.trim();
          const rowVehicleLabel = row.vehicle_make_model?.trim() || null;
          const vehicleLabel = row.vehicle_id
            ? rowVehicleLabel || t("work_orders.vehicle_fallback")
            : t("work_orders.vehicle_not_linked");

          return (
            <div className="space-y-1">
              <p className="truncate font-medium text-neutral-900">{clientLabel}</p>
              <p className="truncate text-xs text-neutral-600">
                {t("work_orders.vehicle_in_order")}: {vehicleLabel}
              </p>
            </div>
          );
        }
      },
      {
        id: "money",
        header: t("work_orders.table.financials"),
        align: "right",
        cell: (row) => {
          return (
            <div className="ml-auto w-full max-w-[210px] space-y-1">
              <p className="flex items-center justify-between text-xs text-neutral-600">
                <span>{t("work_orders.kpi.total")}</span>
                <span className="font-semibold tabular-nums text-neutral-900">{formatMoney(row.total_amount)}</span>
              </p>
              <p className="flex items-center justify-between text-xs text-neutral-600">
                <span>{t("work_orders.kpi.paid")}</span>
                <span className="font-semibold tabular-nums text-success">{formatMoney(row.paid_amount)}</span>
              </p>
              <p className="pt-0.5 text-[11px] uppercase tracking-wide text-neutral-500">{paymentStateLabel(row.payment_state, t)}</p>
            </div>
          );
        }
      },
      {
        id: "ops",
        header: t("work_orders.table.status_actions"),
        cell: (row) => {
          const remaining = parseMoney(row.remaining_amount);
          const hasFullPayment = remaining <= 0;
          const transition =
            row.status === "new"
              ? {
                  label: t("work_orders.action.start"),
                  onClick: () => statusMutation.mutate({ workOrderId: row.id, status: "in_progress" }),
                  variant: "primary" as const
                }
              : row.status === "in_progress"
                ? {
                    label: hasFullPayment ? t("work_order_detail.set_completed_paid") : t("work_orders.action.complete"),
                    onClick: () =>
                      statusMutation.mutate({ workOrderId: row.id, status: hasFullPayment ? "completed_paid" : "completed_unpaid" }),
                    variant: "primary" as const
                  }
                : row.status === "completed_unpaid"
                  ? hasFullPayment
                    ? {
                      label: t("work_orders.action.mark_paid"),
                      onClick: () => statusMutation.mutate({ workOrderId: row.id, status: "completed_paid" }),
                      variant: "secondary" as const
                    }
                    : null
                  : row.status === "completed_paid"
                    ? {
                        label: t("work_orders.action.close"),
                        onClick: () => closeMutation.mutate(row.id),
                        variant: "secondary" as const
                      }
                    : null;

          return (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="space-y-1">
                <Badge tone={STATUS_TONE[row.status]}>{t(`dashboard.status.${row.status}`)}</Badge>
                <p className="text-xs text-neutral-600">
                  {row.assigned_employee_id
                    ? `${t("work_orders.assignee")}: ${employeesById.get(row.assigned_employee_id) ?? row.assigned_employee_id}`
                    : `${t("work_orders.assignee")}: ${t("work_orders.unassigned")}`}
                </p>
              </div>
              <div className="flex items-center gap-1.5">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={(event) => {
                    event.stopPropagation();
                    router.push(ROUTES.workOrderDetail(row.id) as Route);
                  }}
                  disabled={isRowActionBusy}
                >
                  {t("common.open")}
                </Button>
                {transition ? (
                  <Button
                    size="sm"
                    variant={transition.variant}
                    onClick={(event) => {
                      event.stopPropagation();
                      transition.onClick();
                    }}
                    disabled={isRowActionBusy}
                  >
                    {transition.label}
                  </Button>
                ) : null}
              </div>
            </div>
          );
        }
      }
    ],
    [closeMutation, employeesById, isRowActionBusy, router, rowNumberById, statusMutation, t]
  );

  const hasActiveSearch = Boolean(q || search);
  const summaryItems: Array<{
    id: string;
    label: string;
    value: string | number;
    tone?: "neutral" | "success" | "warning";
    emphasized?: boolean;
  }> = [
    { id: "open", label: t("work_orders.kpi.open"), value: queueStats.openCount, tone: "warning" },
    { id: "completed", label: t("work_orders.kpi.completed"), value: queueStats.completedCount, tone: "success" },
    { id: "unassigned", label: t("work_orders.kpi.unassigned"), value: queueStats.unassignedCount, tone: "neutral" },
    { id: "total", label: t("work_orders.kpi.total"), value: formatMoney(String(totals.totalAmount)), emphasized: true },
    { id: "paid", label: t("work_orders.kpi.paid"), value: formatMoney(String(totals.paidAmount)), tone: "success", emphasized: true }
  ];

  return (
    <PageLayout
      title={t("work_orders.title")}
      subtitle={t("work_orders.subtitle")}
      actions={
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => void workOrdersQuery.refetch()} disabled={workOrdersQuery.isFetching}>
            {t("common.refresh")}
          </Button>
          <Button variant="primary" onClick={() => router.push(ROUTES.workOrderNew as Route)}>
            {t("work_orders.new")}
          </Button>
        </div>
      }
    >
      <div className="space-y-2">
        <div className="rounded-lg border border-neutral-300 bg-neutral-0 px-3 py-2 shadow-sm">
          <div className="grid grid-cols-1 gap-2 xl:grid-cols-[minmax(0,1fr)_180px_220px_auto]">
            <Input
              className="w-full"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t("work_orders.search_placeholder")}
            />

            <Select
              value={statusFilter}
              onChange={(event) => {
                const nextStatus = event.target.value as "all" | WorkOrderStatus;
                setStatusFilter(nextStatus);
                setPage(1);
                updateUrlState({ q, page: 1, status: nextStatus, assignee: assigneeFilter });
              }}
            >
              <option value="all">{t("work_orders.filter.status_all")}</option>
              <option value="new">{t("dashboard.status.new")}</option>
              <option value="in_progress">{t("dashboard.status.in_progress")}</option>
              <option value="completed_unpaid">{t("dashboard.status.completed_unpaid")}</option>
              <option value="completed_paid">{t("dashboard.status.completed_paid")}</option>
              <option value="cancelled">{t("dashboard.status.cancelled")}</option>
            </Select>

            <Select
              value={assigneeFilter}
              onChange={(event) => {
                const nextAssignee = event.target.value;
                setAssigneeFilter(nextAssignee);
                setPage(1);
                updateUrlState({ q, page: 1, status: statusFilter, assignee: nextAssignee });
              }}
            >
              <option value="all">{t("work_orders.filter.assignee_all")}</option>
              <option value="unassigned">{t("work_orders.unassigned")}</option>
              {(employeesQuery.data?.items ?? []).map((employee) => (
                <option key={employee.employee_id} value={employee.employee_id}>
                  {employee.email}
                </option>
              ))}
            </Select>

            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setSearch("");
                setQ("");
                setStatusFilter("all");
                setAssigneeFilter("all");
                setPage(1);
                updateUrlState({ q: "", page: 1, status: "all", assignee: "all" });
              }}
              disabled={!hasActiveSearch && statusFilter === "all" && assigneeFilter === "all"}
            >
              {t("common.reset")}
            </Button>
          </div>
        </div>

        <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
          <div className="grid grid-cols-2 gap-x-3 gap-y-2 md:grid-cols-3 xl:grid-cols-6 xl:gap-x-0">
            {summaryItems.map((item, index) => (
              <div
                key={item.id}
                className={cn(
                  "min-w-0 xl:px-3",
                  index === 0 ? "xl:pl-0" : "xl:border-l xl:border-neutral-200",
                  index === summaryItems.length - 1 ? "xl:pr-0" : ""
                )}
              >
                <SummaryMetric label={item.label} value={item.value} tone={item.tone} emphasized={item.emphasized} />
              </div>
            ))}
          </div>
        </div>

        <DataTable
          columns={columns}
          rows={filteredRows}
          getRowId={(row) => row.id}
          onRowClick={(row) => {
            router.push(ROUTES.workOrderDetail(row.id) as Route);
          }}
          loading={workOrdersQuery.isLoading}
          error={workOrdersQuery.error?.message}
          onRetry={() => void workOrdersQuery.refetch()}
          emptyTitle={t("work_orders.empty.title")}
          emptyDescription={t("work_orders.empty.description")}
          emptyAction={
            <Button variant="primary" onClick={() => router.push(ROUTES.workOrderNew as Route)}>
              {t("work_orders.new")}
            </Button>
          }
          density="compact"
          variant="strong"
          tableClassName="min-w-full"
          pagination={{
            page,
            pageSize: PAGE_SIZE,
            total: workOrdersQuery.data?.total ?? 0,
            onPageChange: (nextPage) => {
              setPage(nextPage);
              updateUrlState({ q, page: nextPage, status: statusFilter, assignee: assigneeFilter });
            }
          }}
        />
      </div>
    </PageLayout>
  );
}
