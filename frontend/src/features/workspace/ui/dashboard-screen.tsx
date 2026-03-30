"use client";

import Link from "next/link";
import type { Route } from "next";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import { cn } from "@/core/lib/utils";
import { Badge, Button, Card } from "@/design-system/primitives";
import { PageLayout, StateBoundary } from "@/design-system/patterns";
import {
  fetchDashboardAnalytics,
  fetchWorkOrders,
  mvpQueryKeys
} from "@/features/workspace/api/mvp-api";
import type {
  AnalyticsMonthlyLoadItem,
  AnalyticsRevenueItem,
  AnalyticsWeekdayLoadItem,
  WorkOrderRecord,
  WorkOrderStatus
} from "@/features/workspace/types/mvp-types";
import { useI18n } from "@/shared/i18n";

function formatCurrency(value: string | number): string {
  const normalized = Number(value);
  if (!Number.isFinite(normalized)) {
    return String(value);
  }

  return normalized.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

function compactPeriod(period: string): string {
  const date = new Date(`${period}-01T00:00:00Z`);
  if (Number.isNaN(date.getTime())) {
    return period;
  }

  return date.toLocaleDateString(undefined, {
    month: "short"
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

function KpiCard({
  title,
  value,
  context,
  tone = "neutral"
}: {
  title: string;
  value: string | number;
  context: string;
  tone?: "neutral" | "warning" | "success" | "primary";
}): JSX.Element {
  return (
    <Card className="relative overflow-hidden border-neutral-200 p-3">
      <div
        className={cn(
          "absolute inset-x-0 top-0 h-0.5",
          tone === "warning"
            ? "bg-warning"
            : tone === "success"
              ? "bg-success"
              : tone === "primary"
                ? "bg-primary"
                : "bg-neutral-300"
        )}
      />
      <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">{title}</p>
      <p className="mt-1 text-[28px] font-semibold leading-8 tabular-nums text-neutral-900">{value}</p>
      <p className="mt-1 text-xs text-neutral-600">{context}</p>
    </Card>
  );
}

function MetricChartCard({
  title,
  subtitle,
  children
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}): JSX.Element {
  return (
    <Card className="border-neutral-200 p-3">
      <div>
        <p className="text-sm font-semibold text-neutral-900">{title}</p>
        <p className="mt-0.5 text-xs text-neutral-600">{subtitle}</p>
      </div>
      {children}
    </Card>
  );
}

function MonthlyColumnChart({
  rows,
  colorClass,
  valueLabel,
  emptyLabel
}: {
  rows: Array<{ period: string; value: number }>;
  colorClass: string;
  valueLabel: string;
  emptyLabel: string;
}): JSX.Element {
  if (!rows.length) {
    return <p className="mt-3 text-sm text-neutral-600">{emptyLabel}</p>;
  }

  const maxValue = Math.max(...rows.map((row) => row.value), 1);

  return (
    <div className="mt-3 space-y-2">
      <div
        className="grid h-36 items-end gap-1.5"
        style={{ gridTemplateColumns: `repeat(${rows.length}, minmax(0, 1fr))` }}
      >
        {rows.map((row) => {
          const percent = Math.max(8, Math.round((row.value / maxValue) * 100));
          return (
            <div key={row.period} className="group flex h-full flex-col justify-end gap-1">
              <div className="relative h-28 rounded-sm bg-neutral-100">
                <div
                  className={cn("absolute inset-x-0 bottom-0 rounded-sm", colorClass)}
                  style={{ height: `${percent}%` }}
                />
              </div>
              <p className="text-center text-[11px] font-medium text-neutral-600">{compactPeriod(row.period)}</p>
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between border-t border-neutral-100 pt-2 text-xs text-neutral-600">
        <span>{valueLabel}</span>
        <span className="font-semibold text-neutral-800">Max: {maxValue}</span>
      </div>
    </div>
  );
}

function RevenueLineChart({
  rows,
  emptyLabel,
  createdLabel,
  paidLabel
}: {
  rows: Array<{ period: string; paidAmount: number; orderAmount: number }>;
  emptyLabel: string;
  createdLabel: string;
  paidLabel: string;
}): JSX.Element {
  if (!rows.length) {
    return <p className="mt-3 text-sm text-neutral-600">{emptyLabel}</p>;
  }

  const values = rows.flatMap((row) => [row.paidAmount, row.orderAmount]);
  const maxValue = Math.max(...values, 1);
  const chartWidth = 100;
  const chartHeight = 44;

  const toPoints = (series: number[]): string => {
    if (!series.length) {
      return "";
    }

    return series
      .map((value, index) => {
        const x = series.length === 1 ? chartWidth / 2 : (index / (series.length - 1)) * chartWidth;
        const y = chartHeight - (value / maxValue) * chartHeight;
        return `${x},${Math.max(1, Math.min(chartHeight - 1, y))}`;
      })
      .join(" ");
  };

  const paidSeries = rows.map((row) => row.paidAmount);
  const orderSeries = rows.map((row) => row.orderAmount);

  return (
    <div className="mt-3 space-y-2">
      <div className="rounded-md border border-neutral-100 bg-neutral-50 p-2">
        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="h-36 w-full" preserveAspectRatio="none" aria-hidden>
          <polyline
            fill="none"
            stroke="hsl(var(--primary))"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            points={toPoints(orderSeries)}
          />
          <polyline
            fill="none"
            stroke="hsl(var(--success))"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            points={toPoints(paidSeries)}
          />
        </svg>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-md border border-neutral-200 bg-neutral-0 p-2">
          <p className="font-medium text-neutral-600">{createdLabel}</p>
          <p className="mt-1 font-semibold tabular-nums text-primary">{formatCurrency(orderSeries[orderSeries.length - 1] ?? 0)}</p>
        </div>
        <div className="rounded-md border border-neutral-200 bg-neutral-0 p-2">
          <p className="font-medium text-neutral-600">{paidLabel}</p>
          <p className="mt-1 font-semibold tabular-nums text-success">{formatCurrency(paidSeries[paidSeries.length - 1] ?? 0)}</p>
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-neutral-100 pt-2 text-[11px] text-neutral-600">
        <span>{compactPeriod(rows[0]?.period ?? "")}</span>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-primary" />
            {createdLabel}
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-success" />
            {paidLabel}
          </span>
        </div>
        <span>{compactPeriod(rows[rows.length - 1]?.period ?? "")}</span>
      </div>
    </div>
  );
}

function WeekdayLoadCard({
  title,
  rows,
  locale,
  emptyLabel
}: {
  title: string;
  rows: AnalyticsWeekdayLoadItem[];
  locale: "ru" | "en";
  emptyLabel: string;
}): JSX.Element {
  const weekdayLabels: Record<string, string> =
    locale === "ru"
      ? {
          mon: "Пн",
          tue: "Вт",
          wed: "Ср",
          thu: "Чт",
          fri: "Пт",
          sat: "Сб",
          sun: "Вс"
        }
      : {
          mon: "Mon",
          tue: "Tue",
          wed: "Wed",
          thu: "Thu",
          fri: "Fri",
          sat: "Sat",
          sun: "Sun"
        };

  if (!rows.length) {
    return (
      <Card className="border-neutral-200 p-3">
        <p className="text-sm font-semibold text-neutral-900">{title}</p>
        <p className="mt-3 text-sm text-neutral-600">{emptyLabel}</p>
      </Card>
    );
  }

  const maxValue = Math.max(...rows.map((row) => row.orders_count), 1);

  return (
    <Card className="border-neutral-200 p-3">
      <p className="text-sm font-semibold text-neutral-900">{title}</p>
      <div className="mt-3 grid grid-cols-7 gap-1.5">
        {rows.map((row) => {
          const ratio = row.orders_count / maxValue;
          const toneClass = ratio >= 0.75 ? "bg-primary/30" : ratio >= 0.4 ? "bg-primary/20" : ratio > 0 ? "bg-primary/10" : "bg-neutral-100";

          return (
            <div key={row.weekday} className="space-y-1 text-center">
              <div className={cn("rounded-md border border-neutral-200 px-1 py-1.5", toneClass)}>
                <p className="text-sm font-semibold tabular-nums text-neutral-900">{row.orders_count}</p>
              </div>
              <p className="text-[11px] text-neutral-600">{weekdayLabels[row.weekday] ?? row.weekday}</p>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function RankedListCard({
  title,
  rows,
  emptyLabel,
  labelFormatter
}: {
  title: string;
  rows: Array<{ label: string; value: number }>;
  emptyLabel: string;
  labelFormatter?: (label: string) => string;
}): JSX.Element {
  return (
    <Card className="border-neutral-200 p-3">
      <p className="text-sm font-semibold text-neutral-900">{title}</p>
      {rows.length ? (
        <ul className="mt-3 space-y-1.5">
          {rows.map((row, index) => (
            <li key={`${row.label}-${index}`} className="flex items-center justify-between rounded-md border border-neutral-100 px-2 py-1.5">
              <p className="truncate text-sm text-neutral-700">
                <span className="mr-1 text-neutral-500">{index + 1}.</span>
                {labelFormatter ? labelFormatter(row.label) : row.label}
              </p>
              <span className="rounded-sm bg-neutral-100 px-1.5 py-0.5 text-xs font-semibold tabular-nums text-neutral-800">{row.value}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-neutral-600">{emptyLabel}</p>
      )}
    </Card>
  );
}

export function DashboardScreen(): JSX.Element {
  const { t, locale } = useI18n();

  const analyticsQuery = useQuery({
    queryKey: mvpQueryKeys.dashboardAnalytics(12),
    queryFn: () => fetchDashboardAnalytics(12)
  });

  const workOrdersQuery = useQuery({
    queryKey: mvpQueryKeys.workOrders("", 20, 0),
    queryFn: () => fetchWorkOrders({ q: "", limit: 20, offset: 0 })
  });

  const activeWorkOrders = useMemo<WorkOrderRecord[]>(() => {
    const rows = workOrdersQuery.data?.items ?? [];
    return rows.filter((row) => row.status === "new" || row.status === "in_progress").slice(0, 8);
  }, [workOrdersQuery.data?.items]);

  const monthlyOrdersRows = useMemo(() => {
    return (analyticsQuery.data?.seasonality_monthly ?? []).slice(-6).map((item: AnalyticsMonthlyLoadItem) => ({
      period: item.period,
      value: item.orders_count
    }));
  }, [analyticsQuery.data?.seasonality_monthly]);

  const monthlyClientsRows = useMemo(() => {
    return (analyticsQuery.data?.seasonality_monthly ?? []).slice(-6).map((item: AnalyticsMonthlyLoadItem) => ({
      period: item.period,
      value: item.clients_count
    }));
  }, [analyticsQuery.data?.seasonality_monthly]);

  const revenueRows = useMemo(() => {
    return (analyticsQuery.data?.revenue_monthly ?? []).slice(-6).map((item: AnalyticsRevenueItem) => ({
      period: item.period,
      paidAmount: Number(item.paid_amount) || 0,
      orderAmount: Number(item.order_amount) || 0
    }));
  }, [analyticsQuery.data?.revenue_monthly]);

  const sourceRows = useMemo(
    () =>
      (analyticsQuery.data?.client_sources ?? []).map((item) => ({
        label: item.source,
        value: item.clients_count
      })),
    [analyticsQuery.data?.client_sources]
  );

  const serviceRows = useMemo(
    () =>
      (analyticsQuery.data?.popular_services ?? []).map((item) => ({
        label: item.name,
        value: item.usage_count
      })),
    [analyticsQuery.data?.popular_services]
  );

  return (
    <PageLayout title={t("dashboard.title")} subtitle={t("dashboard.subtitle")}>
      <Card className="border-neutral-200 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-sm font-semibold text-neutral-900">{t("dashboard.quick_actions.title")}</p>
            <p className="text-xs text-neutral-600">{t("dashboard.quick_actions.description")}</p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <Link href={ROUTES.workOrderNew as Route}>
              <Button variant="primary" size="sm">{t("dashboard.quick_actions.create_work_order")}</Button>
            </Link>
            <Link href={ROUTES.clients as Route}>
              <Button variant="secondary" size="sm">{t("dashboard.quick_actions.add_client")}</Button>
            </Link>
            <Link href={ROUTES.vehicles as Route}>
              <Button variant="secondary" size="sm">{t("dashboard.quick_actions.add_vehicle")}</Button>
            </Link>
          </div>
        </div>
      </Card>

      <StateBoundary loading={analyticsQuery.isLoading} error={analyticsQuery.error?.message}>
        {analyticsQuery.data ? (
          <section className="space-y-2">
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-4">
              <KpiCard
                title={t("dashboard.kpi.clients_total")}
                value={analyticsQuery.data.clients_total}
                context={t("dashboard.analytics.client_seasonality")}
                tone="neutral"
              />
              <KpiCard
                title={t("dashboard.kpi.orders_total")}
                value={analyticsQuery.data.work_orders_total}
                context={t("dashboard.analytics.orders_seasonality")}
                tone="primary"
              />
              <KpiCard
                title={t("dashboard.kpi.open_queue")}
                value={analyticsQuery.data.open_work_orders_count}
                context={t("dashboard.kpi.needs_attention")}
                tone="warning"
              />
              <KpiCard
                title={t("dashboard.kpi.paid_30d")}
                value={formatCurrency(analyticsQuery.data.paid_amount_30d)}
                context={t("dashboard.kpi.revenue_context")}
                tone="success"
              />
            </div>

            <div className="grid grid-cols-1 gap-2 xl:grid-cols-3">
              <MetricChartCard title={t("dashboard.analytics.orders_seasonality")} subtitle={t("dashboard.analytics.orders_line")}>
                <MonthlyColumnChart
                  rows={monthlyOrdersRows}
                  colorClass="bg-primary"
                  valueLabel={t("dashboard.analytics.orders_line")}
                  emptyLabel={t("dashboard.operational.empty")}
                />
              </MetricChartCard>

              <MetricChartCard title={t("dashboard.analytics.client_seasonality")} subtitle={t("dashboard.analytics.clients_line")}>
                <MonthlyColumnChart
                  rows={monthlyClientsRows}
                  colorClass="bg-neutral-700"
                  valueLabel={t("dashboard.analytics.clients_line")}
                  emptyLabel={t("dashboard.operational.empty")}
                />
              </MetricChartCard>

              <MetricChartCard title={t("dashboard.analytics.revenue_dynamics")} subtitle={t("dashboard.analytics.paid_line") + " / " + t("dashboard.analytics.created_line")}>
                <RevenueLineChart
                  rows={revenueRows}
                  emptyLabel={t("dashboard.operational.empty")}
                  createdLabel={t("dashboard.analytics.created_line")}
                  paidLabel={t("dashboard.analytics.paid_line")}
                />
              </MetricChartCard>
            </div>

            <div className="grid grid-cols-1 gap-2 xl:grid-cols-3">
              <WeekdayLoadCard
                title={t("dashboard.operational.weekday_load")}
                rows={analyticsQuery.data.load_by_weekday as AnalyticsWeekdayLoadItem[]}
                locale={locale}
                emptyLabel={t("dashboard.operational.empty")}
              />

              <RankedListCard
                title={t("dashboard.operational.source_breakdown")}
                rows={sourceRows}
                emptyLabel={t("dashboard.operational.empty")}
                labelFormatter={(label) => (label === "unknown" ? t("dashboard.operational.unknown_source") : label)}
              />

              <RankedListCard
                title={t("dashboard.operational.popular_services")}
                rows={serviceRows}
                emptyLabel={t("dashboard.operational.popular_services_empty")}
              />
            </div>
          </section>
        ) : null}
      </StateBoundary>

      <Card className="border-neutral-200 p-3">
        <div className="mb-3 flex items-center justify-between gap-2 border-b border-neutral-100 pb-2">
          <div>
            <p className="text-sm font-semibold text-neutral-900">{t("dashboard.active_orders.title")}</p>
            <p className="text-xs text-neutral-600">{t("dashboard.active_orders.description")}</p>
          </div>
          <Link href={ROUTES.workOrders as Route}>
            <Button size="sm" variant="secondary">{t("dashboard.active_orders.all")}</Button>
          </Link>
        </div>

        {workOrdersQuery.isLoading ? (
          <p className="text-sm text-neutral-600">{t("common.loading")}</p>
        ) : workOrdersQuery.error ? (
          <p className="text-sm text-error">{workOrdersQuery.error.message}</p>
        ) : activeWorkOrders.length ? (
          <div className="space-y-1.5">
            {activeWorkOrders.map((order) => (
              <Link
                key={order.id}
                href={ROUTES.workOrderDetail(order.id) as Route}
                className="block rounded-md border border-neutral-200 bg-neutral-50 p-2.5 transition-colors hover:border-neutral-300 hover:bg-neutral-0"
              >
                <div className="grid grid-cols-1 gap-2 lg:grid-cols-[minmax(0,1fr)_auto_auto] lg:items-center">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-neutral-900">
                      {order.description || `Work order #${order.id.slice(0, 8)}`}
                    </p>
                    <p className="mt-0.5 truncate text-xs text-neutral-600">
                      {(order.client_name?.trim() || t("dashboard.client_fallback"))}
                      {" | "}
                      {order.vehicle_id
                        ? order.vehicle_make_model?.trim() || t("dashboard.vehicle_fallback")
                        : t("dashboard.no_vehicle_linked")}
                    </p>
                  </div>

                  <Badge tone={statusTone(order.status)}>{t(`dashboard.status.${order.status}`)}</Badge>

                  <div className="text-left lg:text-right">
                    <p className="text-[11px] uppercase tracking-wide text-neutral-500">{t("dashboard.total_amount")}</p>
                    <p className="text-sm font-semibold tabular-nums text-neutral-900">{formatCurrency(order.total_amount)}</p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="rounded-md border border-dashed border-neutral-300 bg-neutral-50 p-3">
            <p className="text-sm font-medium text-neutral-800">{t("dashboard.active_orders.empty_title")}</p>
            <p className="mt-1 text-sm text-neutral-600">{t("dashboard.active_orders.empty_description")}</p>
            <div className="mt-2">
              <Link href={ROUTES.workOrderNew as Route}>
                <Button size="sm" variant="primary">{t("dashboard.active_orders.empty_action")}</Button>
              </Link>
            </div>
          </div>
        )}
      </Card>
    </PageLayout>
  );
}


