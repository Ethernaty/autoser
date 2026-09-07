"use client";

import Link from "next/link";
import type { Route } from "next";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, CircleDollarSign, Plus, UserPlus2 } from "lucide-react";

import { ROUTES } from "@/core/config/routes";
import { cn } from "@/core/lib/utils";
import { PageLayout, StateBoundary } from "@/design-system/patterns";
import { Badge, Button, Card, Select } from "@/design-system/primitives";
import {
  fetchDashboardAnalytics,
  fetchDashboardSummary,
  fetchEmployees,
  fetchWorkOrders,
  mvpQueryKeys
} from "@/features/workspace/api/mvp-api";
import type {
  DashboardActivity,
  DashboardAssigneeScope,
  DashboardStatusScope,
  WorkOrderPaymentState,
  WorkOrderStatus
} from "@/features/workspace/types/mvp-types";
import { useI18n } from "@/shared/i18n";

type PeriodScope = 3 | 6 | 12;

const statusOptions: Array<{ value: DashboardStatusScope; labelKey: string }> = [
  { value: "all", labelKey: "work_orders.view.all" },
  { value: "active", labelKey: "dashboard.scope.active" },
  { value: "new", labelKey: "dashboard.status.new" },
  { value: "in_progress", labelKey: "dashboard.status.in_progress" },
  { value: "completed_unpaid", labelKey: "dashboard.status.completed_unpaid_short" },
  { value: "completed_paid", labelKey: "dashboard.status.completed_paid_short" },
  { value: "cancelled", labelKey: "dashboard.status.cancelled" }
];

const periodOptions: Array<{ value: PeriodScope; labelKey: string }> = [
  { value: 3, labelKey: "dashboard.period.3m" },
  { value: 6, labelKey: "dashboard.period.6m" },
  { value: 12, labelKey: "dashboard.period.12m" }
];

const STATUS_TONE: Record<WorkOrderStatus, "neutral" | "warning" | "success" | "error"> = {
  new: "neutral",
  in_progress: "warning",
  completed_unpaid: "warning",
  completed_paid: "success",
  cancelled: "error"
};

function parseAmount(value: string | number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatCurrency(value: string | number): string {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return String(value);
  return parsed.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatMonthLabel(period: string, locale: "ru" | "en"): string {
  const date = new Date(`${period}-01T00:00:00`);
  if (Number.isNaN(date.getTime())) return period;
  return date.toLocaleDateString(locale === "ru" ? "ru-RU" : "en-US", { month: "short" });
}

function paymentTone(state: WorkOrderPaymentState): "success" | "warning" | "error" {
  if (state === "paid") return "success";
  if (state === "partial") return "warning";
  return "error";
}

function paymentLabel(state: WorkOrderPaymentState, t: (key: string) => string): string {
  if (state === "paid") return t("work_orders.payment_state.paid");
  if (state === "partial") return t("work_orders.payment_state.partial");
  return t("work_orders.payment_state.unpaid");
}

function resolveActivityTypeKey(entity: string): string {
  if (entity.includes("order")) return "dashboard.activity.type.order";
  if (entity.includes("payment")) return "dashboard.activity.type.payment";
  if (entity.includes("line")) return "dashboard.activity.type.line";
  if (entity.includes("client")) return "dashboard.activity.type.client";
  if (entity.includes("vehicle")) return "dashboard.activity.type.vehicle";
  return "dashboard.activity.type.system";
}

function resolveActivityTitleKey(activity: DashboardActivity): string {
  const action = activity.action.toLowerCase();
  const entity = activity.entity.toLowerCase();

  if (entity.includes("payment") || action.includes("payment")) return "dashboard.activity.event.payment_recorded";
  if (action.includes("assign")) return "dashboard.activity.event.order_assignee_changed";
  if (action.includes("status")) return "dashboard.activity.event.order_status_changed";
  if (action.includes("close")) return "dashboard.activity.event.order_closed";
  if (action.includes("cancel")) return "dashboard.activity.event.order_cancelled";
  if (entity.includes("line")) return "dashboard.activity.event.line_items_changed";
  if (entity.includes("client") && action.includes("create")) return "dashboard.activity.event.client_created";
  if (entity.includes("vehicle") && action.includes("create")) return "dashboard.activity.event.vehicle_created";
  if (entity.includes("order") && action.includes("create")) return "dashboard.activity.event.order_created";
  if (entity.includes("order")) return "dashboard.activity.event.order_updated";
  return "dashboard.activity.event.generic";
}

function resolveActivityReference(activity: DashboardActivity, t: (key: string, vars?: Record<string, string>) => string): string {
  const id = activity.entity_id ? activity.entity_id.slice(0, 6) : "";
  const entity = activity.entity.toLowerCase();

  if (entity.includes("order")) return activity.entity_id ? t("dashboard.activity.ref.order", { id }) : t("dashboard.activity.ref.order_generic");
  if (entity.includes("client")) return activity.entity_id ? t("dashboard.activity.ref.client", { id }) : t("dashboard.activity.ref.client_generic");
  if (entity.includes("vehicle")) return activity.entity_id ? t("dashboard.activity.ref.vehicle", { id }) : t("dashboard.activity.ref.vehicle_generic");
  if (entity.includes("line")) return t("dashboard.activity.ref.line");
  if (entity.includes("payment")) return t("dashboard.activity.ref.payment");
  return t("dashboard.activity.ref.order_generic");
}

function KpiTile({
  title,
  value,
  tone = "neutral"
}: {
  title: string;
  value: string | number;
  tone?: "neutral" | "warning" | "success" | "primary";
}): JSX.Element {
  return (
    <div className="rounded-xl border border-neutral-200 bg-neutral-0 px-3 py-2 shadow-sm">
      <p className="truncate text-[10px] font-semibold uppercase tracking-[0.08em] text-neutral-500">{title}</p>
      <p
        className={cn(
          "mt-1 text-xl font-semibold leading-6 tabular-nums",
          tone === "success"
            ? "text-success"
            : tone === "warning"
              ? "text-warning"
              : tone === "primary"
                ? "text-primary"
                : "text-neutral-900"
        )}
      >
        {value}
      </p>
    </div>
  );
}

function MonthTrendChart({
  rows,
  locale,
  emptyLabel
}: {
  rows: Array<{ period: string; value: number }>;
  locale: "ru" | "en";
  emptyLabel: string;
}): JSX.Element {
  if (!rows.length) {
    return <p className="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 px-3 py-2 text-xs text-neutral-600">{emptyLabel}</p>;
  }

  const maxValue = Math.max(...rows.map((row) => row.value), 1);
  const width = 100;
  const height = 24;
  const labelsStep = rows.length > 8 ? 2 : 1;
  const points = rows
    .map((row, index) => {
      const x = rows.length === 1 ? width / 2 : (index / (rows.length - 1)) * width;
      const y = height - (row.value / maxValue) * height;
      return `${x},${Math.max(1, Math.min(height - 1, y))}`;
    })
    .join(" ");

  return (
    <div className="space-y-2">
      <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-2">
        <svg viewBox={`0 0 ${width} ${height}`} className="h-24 w-full" preserveAspectRatio="none" aria-hidden>
          <polyline
            fill="none"
            stroke="hsl(var(--primary))"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            points={points}
          />
        </svg>
      </div>
      <div className="grid grid-cols-6 gap-1 text-[10px] text-neutral-500 sm:grid-cols-12">
        {rows.map((row, index) => (
          <span key={row.period} className="text-center">
            {index % labelsStep === 0 || index === rows.length - 1 ? formatMonthLabel(row.period, locale) : ""}
          </span>
        ))}
      </div>
    </div>
  );
}

function activityDotClass(typeKey: string): string {
  if (typeKey.includes("payment")) return "bg-success";
  if (typeKey.includes("line")) return "bg-warning";
  if (typeKey.includes("system")) return "bg-neutral-400";
  if (typeKey.includes("client") || typeKey.includes("vehicle")) return "bg-primary";
  return "bg-primary";
}

export function DashboardScreen(): JSX.Element {
  const { t, locale } = useI18n();
  const [periodScope, setPeriodScope] = useState<PeriodScope>(6);
  const [statusScope, setStatusScope] = useState<DashboardStatusScope>("all");
  const [assigneeScope, setAssigneeScope] = useState<DashboardAssigneeScope>("all");

  const analyticsQuery = useQuery({
    queryKey: mvpQueryKeys.dashboardAnalytics(periodScope, statusScope, assigneeScope),
    queryFn: () => fetchDashboardAnalytics({ months: periodScope, status_scope: statusScope, assignee_scope: assigneeScope })
  });

  const summaryQuery = useQuery({
    queryKey: mvpQueryKeys.dashboardSummary,
    queryFn: () => fetchDashboardSummary(8)
  });

  const employeesQuery = useQuery({
    queryKey: mvpQueryKeys.employees("", "", 100, 0),
    queryFn: () => fetchEmployees({ q: "", limit: 100, offset: 0 })
  });

  const workOrdersQuery = useQuery({
    queryKey: mvpQueryKeys.workOrders("", 1, 0, statusScope, assigneeScope),
    queryFn: () =>
      fetchWorkOrders({
        q: "",
        limit: 1,
        offset: 0,
        status_scope: statusScope,
        assignee_scope: assigneeScope
      })
  });

  const queueScope = statusScope === "all" ? "active" : statusScope;
  const queueQuery = useQuery({
    queryKey: mvpQueryKeys.workOrders("", 8, 0, queueScope, assigneeScope),
    queryFn: () => fetchWorkOrders({ limit: 8, offset: 0, status_scope: queueScope, assignee_scope: assigneeScope })
  });

  const assigneeOptions = useMemo(() => {
    const employees = employeesQuery.data?.items ?? [];
    return [
      { value: "all", label: t("work_orders.view.all") },
      { value: "unassigned", label: t("work_orders.unassigned") },
      ...employees.map((employee) => ({
        value: employee.employee_id,
        label: employee.full_name?.trim() || employee.email || employee.employee_id.slice(0, 6)
      }))
    ];
  }, [employeesQuery.data?.items, t]);

  const employeeNameMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const employee of employeesQuery.data?.items ?? []) {
      map.set(employee.employee_id, employee.full_name?.trim() || employee.email || employee.employee_id.slice(0, 6));
    }
    return map;
  }, [employeesQuery.data?.items]);

  const queueRows = queueQuery.data?.items ?? [];
  const registrySummary = workOrdersQuery.data?.summary;
  const queueOutstandingAmount = parseAmount(registrySummary?.outstanding_amount ?? 0);
  const unassignedCount = registrySummary?.unassigned_count ?? 0;
  const completedAndPaidCount = registrySummary?.completed_paid_count ?? 0;

  const monthlyRows = useMemo(
    () =>
      (analyticsQuery.data?.seasonality_monthly ?? []).slice(-periodScope).map((item) => ({
        period: item.period,
        value: item.orders_count
      })),
    [analyticsQuery.data?.seasonality_monthly, periodScope]
  );

  const collectionRate = useMemo(() => {
    const paid = Math.max(0, parseAmount(registrySummary?.paid_amount ?? 0) - parseAmount(registrySummary?.cancelled_paid_amount ?? 0));
    const unpaid = queueOutstandingAmount;
    const total = paid + unpaid;
    if (total <= 0) return 0;
    return Math.round((paid / total) * 100);
  }, [registrySummary, queueOutstandingAmount]);

  const activityRows = useMemo(() => {
    return (summaryQuery.data?.recent_activity ?? []).slice(0, 5).map((activity) => ({
      id: activity.id,
      typeKey: resolveActivityTypeKey(activity.entity),
      titleKey: resolveActivityTitleKey(activity),
      reference: resolveActivityReference(activity, t),
      absoluteTime: formatDateTime(activity.created_at)
    }));
  }, [summaryQuery.data?.recent_activity, t]);

  const topSources = (analyticsQuery.data?.client_sources ?? []).slice(0, 3);
  const topServices = (analyticsQuery.data?.popular_services ?? []).slice(0, 3);
  const problematicOrders = analyticsQuery.data?.problematic_orders ?? [];

  const filtersDirty = periodScope !== 6 || statusScope !== "all" || assigneeScope !== "all";

  return (
    <PageLayout
      title={t("dashboard.title")}
      subtitle={t("dashboard.subtitle")}
      actions={
        <Link href={ROUTES.workOrderNew as Route}>
          <Button size="sm" variant="primary" className="h-9 rounded-lg px-3 text-xs">
            <Plus className="h-3.5 w-3.5" />
            {t("dashboard.quick_actions.create_work_order")}
          </Button>
        </Link>
      }
      className="space-y-3"
    >
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <p className="mr-1 text-[11px] font-semibold text-neutral-500">{t("dashboard.quick_actions.title")}</p>
          <Link href={ROUTES.clients as Route}>
            <Button size="sm" variant="secondary" className="h-8 rounded-lg px-2.5 text-xs">
              <UserPlus2 className="h-3.5 w-3.5" />
              {t("dashboard.quick_actions.add_client")}
            </Button>
          </Link>
          <Link href={ROUTES.vehicles as Route}>
            <Button size="sm" variant="secondary" className="h-8 rounded-lg px-2.5 text-xs">
              <Plus className="h-3.5 w-3.5" />
              {t("dashboard.quick_actions.add_vehicle")}
            </Button>
          </Link>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5">
            <label className="text-[11px] font-semibold text-neutral-500">{t("dashboard.filters.period")}</label>
            <Select
              value={String(periodScope)}
              onChange={(event) => setPeriodScope(Number(event.target.value) as PeriodScope)}
              size="sm"
              portal={false}
              className="h-8 min-w-[112px] rounded-lg bg-neutral-50 text-xs"
            >
              {periodOptions.map((option) => (
                <option key={option.value} value={String(option.value)}>
                  {t(option.labelKey)}
                </option>
              ))}
            </Select>
          </div>

          <div className="flex items-center gap-1.5">
            <label className="text-[11px] font-semibold text-neutral-500">{t("dashboard.filters.status")}</label>
            <Select
              value={statusScope}
              onChange={(event) => setStatusScope(event.target.value as DashboardStatusScope)}
              size="sm"
              portal={false}
              className="h-8 min-w-[128px] rounded-lg bg-neutral-50 text-xs"
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {t(option.labelKey)}
                </option>
              ))}
            </Select>
          </div>

          <div className="flex items-center gap-1.5">
            <label className="text-[11px] font-semibold text-neutral-500">{t("dashboard.filters.executor")}</label>
            <Select
              value={assigneeScope}
              onChange={(event) => setAssigneeScope(event.target.value as DashboardAssigneeScope)}
              size="sm"
              portal={false}
              className="h-8 min-w-[150px] rounded-lg bg-neutral-50 text-xs"
            >
              {assigneeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>

          {filtersDirty ? (
            <button
              type="button"
              className="h-8 rounded-lg px-2 text-xs font-medium text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-800 sm:ml-auto"
              onClick={() => {
                setPeriodScope(6);
                setStatusScope("all");
                setAssigneeScope("all");
              }}
            >
              {t("dashboard.filters.clear")}
            </button>
          ) : null}
        </div>
      </div>

      <StateBoundary
        loading={analyticsQuery.isLoading || workOrdersQuery.isLoading || queueQuery.isLoading}
        error={analyticsQuery.error?.message ?? workOrdersQuery.error?.message ?? queueQuery.error?.message}
      >
        {analyticsQuery.data ? (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2 lg:grid-cols-3 2xl:grid-cols-6">
              <KpiTile title={t("dashboard.kpi.open_queue")} value={analyticsQuery.data.open_work_orders_count} tone="warning" />
              <KpiTile title={t("dashboard.kpi.unpaid_orders")} value={analyticsQuery.data.unpaid_orders_count} tone="warning" />
              <KpiTile title={t("dashboard.kpi.paid_30d")} value={formatCurrency(analyticsQuery.data.paid_amount_30d)} tone="success" />
              <KpiTile title={t("dashboard.kpi.orders_total")} value={analyticsQuery.data.work_orders_total} />
              <KpiTile title={t("dashboard.kpi.clients_total")} value={analyticsQuery.data.clients_total} />
              <KpiTile title={t("dashboard.kpi.revenue_total")} value={formatCurrency(summaryQuery.data?.revenue_total ?? 0)} tone="primary" />
            </div>

            <div className="grid min-w-0 gap-3 xl:grid-cols-12 xl:items-start">
              <Card className="min-w-0 self-start border-neutral-200 bg-neutral-0 p-3 shadow-sm xl:col-span-8">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-neutral-900">{t("dashboard.active_orders.title")}</h3>
                    <p className="text-[11px] text-neutral-600">{t("dashboard.active_orders.description")}</p>
                  </div>
                  <Link href={ROUTES.workOrders as Route}>
                    <Button size="sm" variant="secondary" className="h-7 rounded-lg px-2 text-[11px]">
                      {t("dashboard.active_orders.all")}
                    </Button>
                  </Link>
                </div>

                {queueRows.length ? (
                  <>
                    <div className="hidden overflow-hidden rounded-lg border border-neutral-200 md:block">
                      <div className="max-h-[272px] overflow-auto">
                        <table className="w-full min-w-0 text-xs">
                          <thead className="sticky top-0 bg-neutral-50 text-[11px] uppercase tracking-wide text-neutral-500">
                            <tr>
                              <th className="px-2 py-1.5 text-left font-semibold">{t("shell.nav.work_orders")}</th>
                              <th className="px-2 py-1.5 text-left font-semibold">{t("shell.nav.clients")} / {t("shell.nav.vehicles")}</th>
                              <th className="px-2 py-1.5 text-left font-semibold">{t("dashboard.filters.status")}</th>
                              <th className="px-2 py-1.5 text-left font-semibold">{t("work_orders.filter.label.payment")}</th>
                              <th className="px-2 py-1.5 text-right font-semibold">{t("dashboard.total_amount")}</th>
                              <th className="px-2 py-1.5 text-right font-semibold">{t("common.actions")}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {queueRows.map((row) => {
                              const assigneeId = row.assigned_employee_ids[0] ?? row.assigned_employee_id ?? "";
                              const assigneeLabel = assigneeId ? employeeNameMap.get(assigneeId) || assigneeId.slice(0, 6) : t("work_orders.unassigned");

                              return (
                                <tr key={row.id} className="border-t border-neutral-100">
                                  <td className="px-2 py-1.5 align-top">
                                    <p className="font-semibold text-neutral-900">#{row.order_number}</p>
                                    <p className="line-clamp-1 text-[11px] text-neutral-600">{row.description || t("dashboard.activity.event.order_created")}</p>
                                    <p className="mt-0.5 text-[10px] text-neutral-500">{formatDateTime(row.updated_at)}</p>
                                  </td>
                                  <td className="px-2 py-1.5 align-top">
                                    <p className="font-medium text-neutral-900">{row.client_name || t("dashboard.client_fallback")}</p>
                                    <p className="line-clamp-1 text-[11px] text-neutral-600">{row.vehicle_make_model || t("dashboard.no_vehicle_linked")}</p>
                                    <p className="mt-0.5 text-[10px] text-neutral-500">{assigneeLabel}</p>
                                  </td>
                                  <td className="px-2 py-1.5 align-top">
                                    <Badge tone={STATUS_TONE[row.status]} className="text-[10px]">
                                      {t(`dashboard.status.${row.status}`)}
                                    </Badge>
                                  </td>
                                  <td className="px-2 py-1.5 align-top">
                                    <Badge tone={paymentTone(row.payment_state)} className="text-[10px]">
                                      {paymentLabel(row.payment_state, t)}
                                    </Badge>
                                    <p className="mt-0.5 text-[10px] text-neutral-600">
                                      {t("work_orders.kpi.paid")}: <span className="font-medium">{formatCurrency(row.paid_amount)}</span>
                                    </p>
                                  </td>
                                  <td className="px-2 py-1.5 text-right align-top font-semibold tabular-nums text-neutral-900">
                                    {formatCurrency(row.total_amount)}
                                  </td>
                                  <td className="px-2 py-1.5 text-right align-top">
                                    <Link href={ROUTES.workOrderDetail(row.id) as Route}>
                                      <Button size="sm" variant="secondary" className="h-7 rounded-md px-2 text-[11px]">
                                        {t("common.open")}
                                      </Button>
                                    </Link>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    <div className="space-y-1.5 md:hidden">
                      {queueRows.slice(0, 5).map((row) => (
                        <Card key={row.id} className="border-neutral-200 bg-neutral-50 p-2">
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <p className="text-xs font-semibold text-neutral-900">#{row.order_number}</p>
                              <p className="line-clamp-1 text-[11px] text-neutral-600">{row.description || t("dashboard.activity.event.order_created")}</p>
                            </div>
                            <p className="text-xs font-semibold tabular-nums text-neutral-900">{formatCurrency(row.total_amount)}</p>
                          </div>
                          <div className="mt-1.5 flex items-center justify-between gap-2">
                            <Badge tone={STATUS_TONE[row.status]} className="text-[10px]">
                              {t(`dashboard.status.${row.status}`)}
                            </Badge>
                            <Link href={ROUTES.workOrderDetail(row.id) as Route}>
                              <Button size="sm" variant="secondary" className="h-7 rounded-md px-2 text-[11px]">
                                {t("common.open")}
                              </Button>
                            </Link>
                          </div>
                        </Card>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 p-3">
                    <p className="text-sm font-semibold text-neutral-900">{t("dashboard.active_orders.empty_title")}</p>
                    <p className="mt-1 text-xs text-neutral-600">{t("dashboard.active_orders.empty_description")}</p>
                    <div className="mt-2">
                      <Link href={ROUTES.workOrderNew as Route}>
                        <Button size="sm" variant="primary" className="h-8 rounded-lg px-2.5 text-xs">
                          <Plus className="h-3.5 w-3.5" />
                          {t("dashboard.active_orders.empty_action")}
                        </Button>
                      </Link>
                    </div>
                  </div>
                )}
              </Card>

              <div className="grid min-w-0 self-start grid-cols-1 gap-3 xl:col-span-4">
                <Card className="border-none bg-[linear-gradient(165deg,#6865EE_0%,#5854DA_52%,#4542BC_100%)] p-2.5 text-white shadow-md dark:bg-[linear-gradient(165deg,#3D3B96_0%,#343275_52%,#272557_100%)]">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold">{t("dashboard.finance.title")}</h3>
                      <p className="text-[11px] text-white/80">{t("dashboard.finance.subtitle")}</p>
                    </div>
                    <CircleDollarSign className="h-4 w-4 text-white/85" />
                  </div>

                  <div className="mt-3 space-y-1.5 text-xs">
                    <div className="flex items-center justify-between rounded-lg bg-white/12 px-2 py-1.5">
                      <span className="text-white/80">{t("work_orders.kpi.paid")}</span>
                      <span className="font-semibold tabular-nums">{formatCurrency(Math.max(0, parseAmount(registrySummary?.paid_amount ?? 0) - parseAmount(registrySummary?.cancelled_paid_amount ?? 0)))}</span>
                    </div>
                    <div className="flex items-center justify-between rounded-lg bg-white/12 px-2 py-1.5">
                      <span className="text-white/80">{t("dashboard.finance.unpaid_amount")}</span>
                      <span className="font-semibold tabular-nums">{formatCurrency(queueOutstandingAmount)}</span>
                    </div>
                    <div className="flex items-center justify-between rounded-lg bg-white/12 px-2 py-1.5">
                      <span className="text-white/80">{t("dashboard.finance.completed_paid_count")}</span>
                      <span className="font-semibold tabular-nums">{completedAndPaidCount}</span>
                    </div>
                  </div>

                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/20">
                    <div className="h-full rounded-full bg-white" style={{ width: `${collectionRate}%` }} />
                  </div>
                  <p className="mt-1 text-[10px] text-white/80">{t("dashboard.finance.collection_rate_short", { value: String(collectionRate) })}</p>
                </Card>

                <Card className="border-neutral-200 bg-neutral-0 p-2.5 shadow-sm">
                  <div className="mb-2 flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-neutral-900">{t("dashboard.operational.title")}</h3>
                    {problematicOrders.length ? <AlertTriangle className="h-4 w-4 text-warning" /> : <CheckCircle2 className="h-4 w-4 text-success" />}
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex items-center justify-between rounded-lg bg-neutral-50 px-2 py-1.5">
                      <span className="text-neutral-600">{t("dashboard.operational.problem_orders")}</span>
                      <span className="font-semibold text-neutral-900">{problematicOrders.length}</span>
                    </div>
                    <div className="flex items-center justify-between rounded-lg bg-neutral-50 px-2 py-1.5">
                      <span className="text-neutral-600">{t("work_orders.unassigned")}</span>
                      <span className="font-semibold text-neutral-900">{unassignedCount}</span>
                    </div>
                    <div className="flex items-center justify-between rounded-lg bg-neutral-50 px-2 py-1.5">
                      <span className="text-neutral-600">{t("dashboard.finance.unpaid_amount")}</span>
                      <span className="font-semibold text-neutral-900 tabular-nums">{formatCurrency(queueOutstandingAmount)}</span>
                    </div>
                  </div>
                  {!problematicOrders.length ? <p className="mt-2 text-xs text-neutral-600">{t("dashboard.attention.empty")}</p> : null}
                </Card>
              </div>
            </div>

            <div className="grid min-w-0 grid-cols-1 gap-3 xl:grid-cols-12">
              <Card className="min-w-0 border-neutral-200 bg-neutral-0 p-2.5 shadow-sm xl:col-span-7">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-neutral-900">{t("dashboard.analytics.orders_seasonality")}</h3>
                    <p className="text-[11px] text-neutral-600">{t("dashboard.chart.caption")}</p>
                  </div>
                  <Badge tone="primary" className="text-[10px]">
                    {t("dashboard.chart.period_badge", { months: String(periodScope) })}
                  </Badge>
                </div>
                <MonthTrendChart rows={monthlyRows} locale={locale} emptyLabel={t("dashboard.analytics.empty")} />
              </Card>

              <Card className="min-w-0 border-neutral-200 bg-neutral-0 p-2.5 shadow-sm xl:col-span-5">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold text-neutral-900">{t("dashboard.activity.title")}</h3>
                  <Link href={ROUTES.workOrders as Route} className="text-xs font-medium text-primary hover:underline">
                    {t("dashboard.active_orders.all")}
                  </Link>
                </div>

                {activityRows.length ? (
                  <ul className="space-y-1.5">
                    {activityRows.slice(0, 4).map((row) => (
                      <li key={row.id} className="flex items-start gap-2 rounded-lg border border-neutral-100 bg-neutral-50 px-2 py-1.5">
                        <span className={cn("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", activityDotClass(row.typeKey))} aria-hidden />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <p className="line-clamp-1 text-xs font-semibold text-neutral-900">{t(row.titleKey)}</p>
                            <Badge tone="neutral" className="text-[10px]">
                              {t(row.typeKey)}
                            </Badge>
                          </div>
                          <p className="line-clamp-1 text-[11px] text-neutral-600">{row.reference}</p>
                        </div>
                        <span className="shrink-0 text-[10px] text-neutral-500">{row.absoluteTime}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 px-3 py-2 text-xs text-neutral-600">
                    {t("dashboard.activity.empty")}
                  </div>
                )}
              </Card>
            </div>

            <div className="grid min-w-0 grid-cols-1 gap-3 lg:grid-cols-2">
              <Card className="min-w-0 border-neutral-200 bg-neutral-0 p-3 shadow-sm">
                <h3 className="text-sm font-semibold text-neutral-900">{t("dashboard.operational.source_breakdown")}</h3>
                <ul className="mt-2 space-y-1.5 text-xs text-neutral-700">
                  {topSources.length ? (
                    topSources.map((source) => (
                      <li key={source.source} className="flex items-center justify-between rounded-lg bg-neutral-50 px-2 py-1.5">
                        <span className="truncate">{source.source === "unknown" ? t("dashboard.operational.unknown_source") : source.source}</span>
                        <span className="font-semibold">{source.clients_count}</span>
                      </li>
                    ))
                  ) : (
                    <li className="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 px-2 py-2 text-neutral-600">
                      {t("dashboard.operational.empty")}
                    </li>
                  )}
                </ul>
              </Card>

              <Card className="min-w-0 border-neutral-200 bg-neutral-0 p-3 shadow-sm">
                <h3 className="text-sm font-semibold text-neutral-900">{t("dashboard.operational.popular_services")}</h3>
                <ul className="mt-2 space-y-1.5 text-xs text-neutral-700">
                  {topServices.length ? (
                    topServices.map((service) => (
                      <li key={service.name} className="flex items-center justify-between rounded-lg bg-neutral-50 px-2 py-1.5">
                        <span className="truncate">{service.name}</span>
                        <span className="font-semibold">{service.usage_count}</span>
                      </li>
                    ))
                  ) : (
                    <li className="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 px-2 py-2 text-neutral-600">
                      {t("dashboard.operational.popular_services_empty")}
                    </li>
                  )}
                </ul>
              </Card>
            </div>
          </div>
        ) : null}
      </StateBoundary>
    </PageLayout>
  );
}
