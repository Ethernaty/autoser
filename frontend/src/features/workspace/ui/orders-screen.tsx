"use client";

import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, CreditCard, Filter, MoreHorizontal } from "lucide-react";

import { ROUTES } from "@/core/config/routes";
import { cn } from "@/core/lib/utils";
import { Badge, Button, Input, Modal } from "@/design-system/primitives";
import { PageLayout } from "@/design-system/patterns";
import {
  closeWorkOrder,
  fetchEmployees,
  fetchWorkspaceContext,
  fetchWorkOrders,
  mvpQueryKeys,
  setWorkOrderStatus
} from "@/features/workspace/api/mvp-api";
import type { DashboardStatusScope, WorkOrderPaymentState, WorkOrderRecord, WorkOrderStatus } from "@/features/workspace/types/mvp-types";
import { useI18n } from "@/shared/i18n";

const PAGE_SIZE = 20;
const FETCH_LIMIT = 50;
const LOOKUP_LIMIT = 50;

const STATUS_BADGE_TONE: Record<WorkOrderStatus, "neutral" | "warning" | "success" | "error"> = {
  new: "neutral",
  in_progress: "warning",
  completed_unpaid: "warning",
  completed_paid: "success",
  cancelled: "error"
};

const STATUS_SORT_ORDER: Record<WorkOrderStatus, number> = {
  new: 0,
  in_progress: 1,
  completed_unpaid: 2,
  completed_paid: 3,
  cancelled: 4
};

type PaymentScope = "all" | WorkOrderPaymentState;
type DateScope = "all" | "today" | "yesterday" | "7d" | "30d" | "this_month" | "last_month" | "custom";
type SortScope = "updated_desc" | "created_desc" | "amount_desc" | "amount_asc" | "status";
type SavedView = "all" | "active" | "unpaid" | "completed" | "mine" | "custom";

type OrdersListState = {
  q: string;
  page: number;
  statusScope: DashboardStatusScope;
  paymentScope: PaymentScope;
  assigneeScope: string;
  dateScope: DateScope;
  dateFrom: string;
  dateTo: string;
  sortScope: SortScope;
  view: SavedView;
};

const DEFAULT_STATE: OrdersListState = {
  q: "",
  page: 1,
  statusScope: "all",
  paymentScope: "all",
  assigneeScope: "all",
  dateScope: "all",
  dateFrom: "",
  dateTo: "",
  sortScope: "updated_desc",
  view: "all"
};

function formatMoney(value: string | number): string {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return String(value);
  }
  return parsed.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function parseMoney(value: string | number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function parseDateInput(value: string): Date | null {
  if (!value.trim()) return null;
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return null;
  return date;
}

function toDateStart(date: Date): number {
  const copy = new Date(date);
  copy.setHours(0, 0, 0, 0);
  return copy.getTime();
}

function toDateEnd(date: Date): number {
  const copy = new Date(date);
  copy.setHours(23, 59, 59, 999);
  return copy.getTime();
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString();
}

function matchesDateScope(row: WorkOrderRecord, dateScope: DateScope, from: string, to: string): boolean {
  if (dateScope === "all") return true;

  const source = row.updated_at || row.created_at;
  const current = new Date(source);
  if (Number.isNaN(current.getTime())) return false;

  const now = new Date();
  const rowTs = current.getTime();
  const todayStart = toDateStart(now);

  if (dateScope === "today") return rowTs >= todayStart;
  if (dateScope === "yesterday") return rowTs >= todayStart - 24 * 60 * 60 * 1000 && rowTs < todayStart;
  if (dateScope === "7d") return rowTs >= todayStart - 6 * 24 * 60 * 60 * 1000;
  if (dateScope === "30d") return rowTs >= todayStart - 29 * 24 * 60 * 60 * 1000;
  if (dateScope === "this_month") {
    const start = new Date(now.getFullYear(), now.getMonth(), 1).getTime();
    return rowTs >= start;
  }
  if (dateScope === "last_month") {
    const start = new Date(now.getFullYear(), now.getMonth() - 1, 1).getTime();
    const end = new Date(now.getFullYear(), now.getMonth(), 1).getTime();
    return rowTs >= start && rowTs < end;
  }

  const fromDate = parseDateInput(from);
  const toDate = parseDateInput(to);

  if (!fromDate && !toDate) return true;
  if (fromDate && rowTs < toDateStart(fromDate)) return false;
  if (toDate && rowTs > toDateEnd(toDate)) return false;
  return true;
}

function paymentStateLabel(state: WorkOrderPaymentState, t: (key: string) => string): string {
  if (state === "paid") return t("work_orders.payment_state.paid");
  if (state === "partial") return t("work_orders.payment_state.partial");
  return t("work_orders.payment_state.unpaid");
}

function paymentTone(state: WorkOrderPaymentState): "neutral" | "warning" | "success" | "error" {
  if (state === "paid") return "success";
  if (state === "partial") return "warning";
  return "error";
}

function isStatusScope(value: string | null): value is DashboardStatusScope {
  return (
    value === "all" ||
    value === "active" ||
    value === "completed" ||
    value === "cancelled" ||
    value === "completed_unpaid" ||
    value === "new" ||
    value === "in_progress" ||
    value === "completed_paid"
  );
}

function isPaymentScope(value: string | null): value is PaymentScope {
  return value === "all" || value === "unpaid" || value === "partial" || value === "paid";
}

function isDateScope(value: string | null): value is DateScope {
  return (
    value === "all" ||
    value === "today" ||
    value === "yesterday" ||
    value === "7d" ||
    value === "30d" ||
    value === "this_month" ||
    value === "last_month" ||
    value === "custom"
  );
}

function isSortScope(value: string | null): value is SortScope {
  return value === "updated_desc" || value === "created_desc" || value === "amount_desc" || value === "amount_asc" || value === "status";
}

function isSavedView(value: string | null): value is SavedView {
  return value === "all" || value === "active" || value === "unpaid" || value === "completed" || value === "mine" || value === "custom";
}

function isValidAssigneeScope(value: string | null): value is string {
  if (!value) return false;
  if (value === "all" || value === "unassigned") return true;
  if (value.length > 64) return false;
  return /^[a-zA-Z0-9@._:-]+$/.test(value);
}

function parseStateFromUrl(searchParams: { get: (key: string) => string | null }): OrdersListState {
  const q = searchParams.get("q") ?? DEFAULT_STATE.q;
  const pageRaw = Number(searchParams.get("page") ?? `${DEFAULT_STATE.page}`);
  const page = Number.isFinite(pageRaw) && pageRaw > 0 ? pageRaw : DEFAULT_STATE.page;
  const statusRaw = searchParams.get("status_scope");
  const paymentRaw = searchParams.get("payment_scope");
  const assigneeRaw = searchParams.get("assignee_scope");
  const assigneeScope = isValidAssigneeScope(assigneeRaw) ? assigneeRaw : DEFAULT_STATE.assigneeScope;
  const dateRaw = searchParams.get("date_scope");
  const sortRaw = searchParams.get("sort");
  const viewRaw = searchParams.get("view");

  return {
    q,
    page,
    statusScope: isStatusScope(statusRaw) ? statusRaw : DEFAULT_STATE.statusScope,
    paymentScope: isPaymentScope(paymentRaw) ? paymentRaw : DEFAULT_STATE.paymentScope,
    assigneeScope,
    dateScope: isDateScope(dateRaw) ? dateRaw : DEFAULT_STATE.dateScope,
    dateFrom: searchParams.get("date_from") ?? DEFAULT_STATE.dateFrom,
    dateTo: searchParams.get("date_to") ?? DEFAULT_STATE.dateTo,
    sortScope: isSortScope(sortRaw) ? sortRaw : DEFAULT_STATE.sortScope,
    view: isSavedView(viewRaw) ? viewRaw : DEFAULT_STATE.view
  };
}

function getStatusOptions(row: WorkOrderRecord): WorkOrderStatus[] {
  if (row.status === "new") return ["new", "in_progress", "cancelled"];
  if (row.status === "in_progress") return ["in_progress", "completed_unpaid", "completed_paid", "cancelled"];
  if (row.status === "completed_unpaid") return ["completed_unpaid", "completed_paid"];
  if (row.status === "completed_paid") return ["completed_paid"];
  return ["cancelled"];
}

function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }): JSX.Element {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-2 py-0.5 text-[11px] font-medium transition",
        active
          ? "border-primary/35 bg-primary/10 text-primary"
          : "border-neutral-200 bg-transparent text-neutral-600 hover:border-neutral-300 hover:bg-neutral-50"
      )}
    >
      {label}
    </button>
  );
}

type CompactOption<T extends string> = {
  value: T;
  label: string;
};

function CompactFilterMenu<T extends string>({
  menuId,
  openMenuId,
  setOpenMenuId,
  label,
  value,
  options,
  active,
  className,
  onChange,
  keepOpenValues,
  footer,
  scrollable = false
}: {
  menuId: string;
  openMenuId: string | null;
  setOpenMenuId: (next: string | null) => void;
  label: string;
  value: T;
  options: CompactOption<T>[];
  active: boolean;
  className?: string;
  onChange: (next: T) => void;
  keepOpenValues?: T[];
  footer?: (close: () => void) => JSX.Element | null;
  scrollable?: boolean;
}): JSX.Element {
  const closeMenu = (): void => {
    setOpenMenuId(null);
  };

  return (
    <details className={cn("relative shrink-0", className)} open={openMenuId === menuId} data-filter-menu-root="true">
      <summary
        onClick={(event) => {
          event.preventDefault();
          setOpenMenuId(openMenuId === menuId ? null : menuId);
        }}
        className={cn(
          "flex h-8 list-none items-center justify-between gap-1 rounded-md border px-2.5 text-xs font-medium transition",
          active
            ? "border-primary/35 bg-primary/10 text-primary"
            : "border-neutral-200 bg-neutral-50 text-neutral-700 hover:border-neutral-300 hover:bg-neutral-100"
        )}
      >
        <span>{label}</span>
        <div className="ml-auto flex items-center gap-1">
          {active ? <span className="h-1.5 w-1.5 rounded-full bg-primary" /> : null}
          <ChevronDown className="h-3.5 w-3.5 text-neutral-500" />
        </div>
      </summary>

      <div
        className={cn(
          "absolute left-0 z-30 mt-1.5 min-w-[220px] rounded-xl border border-neutral-200 bg-neutral-0 p-1.5 shadow-lg",
          scrollable ? "max-h-72 overflow-auto" : "overflow-visible"
        )}
      >
        {options.map((option) => (
          <button
            key={`${label}-${option.value}`}
            type="button"
            className={cn(
              "w-full rounded-lg px-2.5 py-1.5 text-left text-xs transition",
              option.value === value ? "bg-primary/10 text-primary" : "text-neutral-800 hover:bg-neutral-100"
            )}
            onClick={() => {
              onChange(option.value);
              if (!(keepOpenValues ?? []).includes(option.value)) {
                closeMenu();
              }
            }}
          >
            {option.label}
          </button>
        ))}
        {footer ? (
          <>
            <div className="my-1 h-px bg-neutral-200" />
            {footer(() => closeMenu())}
          </>
        ) : null}
      </div>
    </details>
  );
}

function TinyMetric({ label, value, tone = "neutral" }: { label: string; value: string | number; tone?: "neutral" | "warning" | "success" }): JSX.Element {
  return (
    <div className="px-2.5 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-neutral-500">{label}</p>
      <p className={cn("mt-0.5 text-base font-semibold leading-5 tabular-nums", tone === "warning" ? "text-warning" : tone === "success" ? "text-success" : "text-neutral-900")}>{value}</p>
    </div>
  );
}

function SkeletonList(): JSX.Element {
  return (
    <div className="space-y-1.5 p-2.5">
      {Array.from({ length: 7 }).map((_, idx) => (
        <div key={`row-skeleton-${idx}`} className="animate-pulse rounded-md border border-neutral-200 bg-neutral-0 p-2.5">
          <div className="h-3 w-40 rounded bg-neutral-100" />
          <div className="mt-2 h-2.5 w-64 rounded bg-neutral-100" />
          <div className="mt-2 h-2.5 w-48 rounded bg-neutral-100" />
        </div>
      ))}
    </div>
  );
}
function DesktopPagination({
  page,
  total,
  onPageChange,
  t
}: {
  page: number;
  total: number;
  onPageChange: (next: number) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
}): JSX.Element | null {
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (total <= PAGE_SIZE) return null;

  return (
    <div className="flex items-center justify-between border-t border-neutral-200 px-3 py-2">
      <p className="text-xs text-neutral-600">{t("datatable.pagination.page", { page: `${page}/${totalPages}` })}</p>
      <div className="flex items-center gap-1.5">
        <Button size="sm" variant="secondary" onClick={() => onPageChange(Math.max(1, page - 1))} disabled={page <= 1}>{t("datatable.pagination.prev")}</Button>
        <Button size="sm" variant="secondary" onClick={() => onPageChange(Math.min(totalPages, page + 1))} disabled={page >= totalPages}>{t("datatable.pagination.next")}</Button>
      </div>
    </div>
  );
}

function RowActionMenu({
  row,
  t,
  disabled,
  compact = false,
  onStatusChange,
  onClose,
  onOpenDetail
}: {
  row: WorkOrderRecord;
  t: (key: string, vars?: Record<string, string | number>) => string;
  disabled: boolean;
  compact?: boolean;
  onStatusChange: (status: WorkOrderStatus) => void;
  onClose: () => void;
  onOpenDetail: () => void;
}): JSX.Element {
  const statusOptions = getStatusOptions(row).filter((status) => status !== row.status);

  const closeMenu = (target: EventTarget | null): void => {
    if (!(target instanceof HTMLElement)) return;
    const details = target.closest("details") as HTMLDetailsElement | null;
    if (details) {
      details.open = false;
    }
  };

  return (
    <details className="relative" onClick={(event) => event.stopPropagation()}>
      <summary
        className={cn(
          "flex h-8 w-8 cursor-pointer list-none items-center justify-center rounded-md border text-neutral-700 transition",
          compact
            ? "border-neutral-200 bg-neutral-50 hover:border-neutral-300 hover:bg-neutral-100"
            : "border-neutral-300 bg-neutral-0 hover:border-neutral-400 hover:bg-neutral-50"
        )}
      >
        <MoreHorizontal className="h-4 w-4" />
      </summary>

      <div className="absolute right-0 z-30 mt-1.5 w-52 rounded-md border border-neutral-200 bg-neutral-0 p-1 shadow-md">
        {statusOptions.length ? (
          <>
            {statusOptions.map((status) => (
              <button
                key={`${row.id}-status-${status}`}
                type="button"
                className="w-full rounded px-2 py-1.5 text-left text-xs font-medium text-neutral-800 hover:bg-neutral-100"
                disabled={disabled}
                onClick={(event) => {
                  closeMenu(event.target);
                  onStatusChange(status);
                }}
              >
                {t(`dashboard.status.${status}`)}
              </button>
            ))}
            <div className="my-1 h-px bg-neutral-200" />
          </>
        ) : null}

        <button
          type="button"
          className="w-full rounded px-2 py-1.5 text-left text-xs text-neutral-800 hover:bg-neutral-100"
          onClick={(event) => {
            closeMenu(event.target);
            onOpenDetail();
          }}
        >
          {t("work_orders.assignee")}
        </button>
        <button
          type="button"
          className="w-full rounded px-2 py-1.5 text-left text-xs text-neutral-800 hover:bg-neutral-100"
          onClick={(event) => {
            closeMenu(event.target);
            onOpenDetail();
          }}
        >
          {t("work_orders.action.record_payment")}
        </button>
        <button
          type="button"
          className="w-full rounded px-2 py-1.5 text-left text-xs text-neutral-800 hover:bg-neutral-100"
          onClick={(event) => {
            closeMenu(event.target);
            onOpenDetail();
          }}
        >
          {t("work_orders.action.view_docs")}
        </button>

        {row.status === "completed_paid" ? (
          <button
            type="button"
            className="mt-1 w-full rounded px-2 py-1.5 text-left text-xs font-medium text-success hover:bg-success/10"
            disabled={disabled}
            onClick={(event) => {
              closeMenu(event.target);
              onClose();
            }}
          >
            {t("work_orders.action.close")}
          </button>
        ) : null}

        {row.status !== "cancelled" ? (
          <button
            type="button"
            className="mt-1 w-full rounded px-2 py-1.5 text-left text-xs font-medium text-error hover:bg-error/10"
            disabled={disabled}
            onClick={(event) => {
              closeMenu(event.target);
              onStatusChange("cancelled");
            }}
          >
            {t("work_orders.action.cancel")}
          </button>
        ) : null}
      </div>
    </details>
  );
}

export function OrdersScreen(): JSX.Element {
  const { t } = useI18n();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  const parsedState = useMemo(() => parseStateFromUrl(searchParams), [searchParams]);

  const [state, setState] = useState<OrdersListState>(parsedState);
  const [searchInput, setSearchInput] = useState(parsedState.q);
  const [isMobileFiltersOpen, setIsMobileFiltersOpen] = useState(false);
  const [openFilterMenu, setOpenFilterMenu] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingRowId, setPendingRowId] = useState<string | null>(null);

  useEffect(() => {
    setState(parsedState);
    setSearchInput(parsedState.q);
  }, [parsedState]);

  const updateUrlState = useCallback(
    (next: OrdersListState): void => {
      const params = new URLSearchParams(searchParams.toString());

      if (next.q) params.set("q", next.q); else params.delete("q");
      if (next.page > 1) params.set("page", String(next.page)); else params.delete("page");
      if (next.statusScope !== "all") params.set("status_scope", next.statusScope); else params.delete("status_scope");
      if (next.paymentScope !== "all") params.set("payment_scope", next.paymentScope); else params.delete("payment_scope");
      if (next.assigneeScope !== "all") params.set("assignee_scope", next.assigneeScope); else params.delete("assignee_scope");
      if (next.dateScope !== "all") params.set("date_scope", next.dateScope); else params.delete("date_scope");
      if (next.dateFrom) params.set("date_from", next.dateFrom); else params.delete("date_from");
      if (next.dateTo) params.set("date_to", next.dateTo); else params.delete("date_to");
      if (next.sortScope !== "updated_desc") params.set("sort", next.sortScope); else params.delete("sort");
      if (next.view !== "all") params.set("view", next.view); else params.delete("view");

      const query = params.toString();
      router.replace((query ? `${pathname}?${query}` : pathname) as Route, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const applyState = useCallback(
    (patch: Partial<OrdersListState>, options?: { resetPage?: boolean; keepView?: boolean }) => {
      setState((prev) => {
        const next: OrdersListState = {
          ...prev,
          ...patch,
          page: options?.resetPage ? 1 : (patch.page ?? prev.page),
          view: options?.keepView ? (patch.view ?? prev.view) : (patch.view ?? "custom")
        };
        updateUrlState(next);
        return next;
      });
    },
    [updateUrlState]
  );

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      const normalized = searchInput.trim();
      if (normalized === state.q) return;
      applyState({ q: normalized }, { resetPage: true });
    }, 220);

    return () => window.clearTimeout(timeoutId);
  }, [applyState, searchInput, state.q]);

  const employeesQuery = useQuery({
    queryKey: mvpQueryKeys.employees("", "", LOOKUP_LIMIT, 0),
    queryFn: () => fetchEmployees({ limit: LOOKUP_LIMIT, offset: 0 })
  });

  const workspaceContextQuery = useQuery({
    queryKey: mvpQueryKeys.workspaceContext,
    queryFn: fetchWorkspaceContext
  });

  const workOrdersQuery = useQuery({
    queryKey: mvpQueryKeys.workOrders(state.q, FETCH_LIMIT, 0, state.statusScope, state.assigneeScope),
    queryFn: () =>
      fetchWorkOrders({
        q: state.q,
        status_scope: state.statusScope,
        assignee_scope: state.assigneeScope,
        limit: FETCH_LIMIT,
        offset: 0
      })
  });

  const statusMutation = useMutation({
    mutationFn: ({ workOrderId, status }: { workOrderId: string; status: WorkOrderStatus }) => setWorkOrderStatus(workOrderId, status),
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

  const employees = useMemo(() => employeesQuery.data?.items ?? [], [employeesQuery.data?.items]);

  const employeesById = useMemo(() => {
    const map = new Map<string, string>();
    employees.forEach((employee) => map.set(employee.employee_id, employee.full_name?.trim() || employee.email));
    return map;
  }, [employees]);

  const currentEmployeeId = useMemo(() => {
    const currentUserId = workspaceContextQuery.data?.user_id;
    if (!currentUserId) return null;
    const matched = employees.find((employee) => employee.user_id === currentUserId);
    return matched?.employee_id ?? null;
  }, [employees, workspaceContextQuery.data?.user_id]);

  const sortedAndFilteredRows = useMemo(() => {
    const source = workOrdersQuery.data?.items ?? [];
    const afterPayment = state.paymentScope === "all" ? source : source.filter((row) => row.payment_state === state.paymentScope);
    const afterDate = afterPayment.filter((row) => matchesDateScope(row, state.dateScope, state.dateFrom, state.dateTo));

    const sorted = [...afterDate];
    sorted.sort((a, b) => {
      if (state.sortScope === "created_desc") return Date.parse(b.created_at) - Date.parse(a.created_at);
      if (state.sortScope === "amount_desc") return parseMoney(b.total_amount) - parseMoney(a.total_amount);
      if (state.sortScope === "amount_asc") return parseMoney(a.total_amount) - parseMoney(b.total_amount);
      if (state.sortScope === "status") return STATUS_SORT_ORDER[a.status] - STATUS_SORT_ORDER[b.status];
      return Date.parse(b.updated_at) - Date.parse(a.updated_at);
    });

    return sorted;
  }, [state.dateFrom, state.dateScope, state.dateTo, state.paymentScope, state.sortScope, workOrdersQuery.data?.items]);

  const totalFiltered = sortedAndFilteredRows.length;
  const totalPages = Math.max(1, Math.ceil(totalFiltered / PAGE_SIZE));

  useEffect(() => {
    if (state.page <= totalPages) return;
    const next = { ...state, page: totalPages };
    setState(next);
    updateUrlState(next);
  }, [state, totalPages, updateUrlState]);

  const pagedRows = useMemo(() => {
    const offset = (state.page - 1) * PAGE_SIZE;
    return sortedAndFilteredRows.slice(offset, offset + PAGE_SIZE);
  }, [sortedAndFilteredRows, state.page]);

  const metrics = useMemo(() => {
    const open = sortedAndFilteredRows.filter((row) => row.status === "new").length;
    const inProgress = sortedAndFilteredRows.filter((row) => row.status === "in_progress").length;
    const completed = sortedAndFilteredRows.filter((row) => row.status === "completed_unpaid" || row.status === "completed_paid").length;
    const unpaid = sortedAndFilteredRows.filter((row) => row.payment_state !== "paid").length;

    let revenue = 0;
    let paid = 0;
    sortedAndFilteredRows.forEach((row) => {
      revenue += parseMoney(row.total_amount);
      paid += parseMoney(row.paid_amount);
    });

    return { open, inProgress, completed, unpaid, revenue, paid };
  }, [sortedAndFilteredRows]);

  const hasAnyFilterActive = useMemo(() => {
    return (
      Boolean(state.q) ||
      state.statusScope !== "all" ||
      state.paymentScope !== "all" ||
      state.assigneeScope !== "all" ||
      state.dateScope !== "all" ||
      Boolean(state.dateFrom) ||
      Boolean(state.dateTo) ||
      state.sortScope !== "updated_desc"
    );
  }, [state]);

  const clearFilters = useCallback(() => {
    setSearchInput("");
    setOpenFilterMenu(null);
    applyState({ ...DEFAULT_STATE }, { keepView: true });
  }, [applyState]);

  useEffect(() => {
    if (!openFilterMenu) {
      return;
    }

    const onPointerDown = (event: MouseEvent): void => {
      const target = event.target as HTMLElement | null;
      if (!target) return;
      if (target.closest("[data-filter-menu-root='true']")) return;
      setOpenFilterMenu(null);
    };

    const onEscape = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setOpenFilterMenu(null);
      }
    };

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onEscape);

    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onEscape);
    };
  }, [openFilterMenu]);

  const applySavedView = useCallback(
    (view: Exclude<SavedView, "custom">) => {
      const base: Partial<OrdersListState> = { view, page: 1, sortScope: "updated_desc" };

      if (view === "all") {
        applyState(
          { ...base, statusScope: "all", paymentScope: "all", assigneeScope: "all", dateScope: "all", dateFrom: "", dateTo: "" },
          { keepView: true }
        );
        return;
      }

      if (view === "active") {
        applyState({ ...base, statusScope: "active", paymentScope: "all", assigneeScope: "all" }, { keepView: true });
        return;
      }

      if (view === "unpaid") {
        applyState({ ...base, statusScope: "all", paymentScope: "unpaid", assigneeScope: "all" }, { keepView: true });
        return;
      }

      if (view === "completed") {
        applyState({ ...base, statusScope: "completed", paymentScope: "all", assigneeScope: "all" }, { keepView: true });
        return;
      }

      applyState({ ...base, statusScope: "active", paymentScope: "all", assigneeScope: currentEmployeeId ?? "all" }, { keepView: true });
    },
    [applyState, currentEmployeeId]
  );

  const setQuickToggle = useCallback(
    (type: "open" | "in_progress" | "unassigned" | "unpaid" | "today") => {
      if (type === "open") {
        applyState({ statusScope: state.statusScope === "active" ? "all" : "active" }, { resetPage: true });
        return;
      }
      if (type === "in_progress") {
        applyState({ statusScope: state.statusScope === "in_progress" ? "all" : "in_progress" }, { resetPage: true });
        return;
      }
      if (type === "unassigned") {
        applyState({ assigneeScope: state.assigneeScope === "unassigned" ? "all" : "unassigned" }, { resetPage: true });
        return;
      }
      if (type === "unpaid") {
        applyState({ paymentScope: state.paymentScope === "unpaid" ? "all" : "unpaid" }, { resetPage: true });
        return;
      }
      applyState({ dateScope: state.dateScope === "today" ? "all" : "today", dateFrom: "", dateTo: "" }, { resetPage: true });
    },
    [applyState, state.assigneeScope, state.dateScope, state.paymentScope, state.statusScope]
  );

  const handleStatusChange = useCallback(
    async (row: WorkOrderRecord, nextStatus: WorkOrderStatus) => {
      if (nextStatus === row.status) return;
      try {
        setActionError(null);
        setPendingRowId(row.id);
        await statusMutation.mutateAsync({ workOrderId: row.id, status: nextStatus });
      } catch (error) {
        setActionError(error instanceof Error ? error.message : t("state.error.title"));
      } finally {
        setPendingRowId(null);
      }
    },
    [statusMutation, t]
  );

  const handleCloseOrder = useCallback(
    async (row: WorkOrderRecord) => {
      try {
        setActionError(null);
        setPendingRowId(row.id);
        await closeMutation.mutateAsync(row.id);
      } catch (error) {
        setActionError(error instanceof Error ? error.message : t("state.error.title"));
      } finally {
        setPendingRowId(null);
      }
    },
    [closeMutation, t]
  );

  const savedViewOptions: Array<{ id: Exclude<SavedView, "custom">; label: string }> = [
    { id: "all", label: t("work_orders.view.all") },
    { id: "active", label: t("work_orders.view.active") },
    { id: "unpaid", label: t("work_orders.view.unpaid") },
    { id: "completed", label: t("work_orders.view.completed") },
    { id: "mine", label: t("work_orders.view.mine") }
  ];

  const renderEmptyState = (filtered: boolean): JSX.Element => (
    <div className="rounded-md border border-neutral-200 bg-neutral-0 px-4 py-8 text-center">
      <p className="text-sm font-semibold text-neutral-900">{filtered ? t("work_orders.no_results.title") : t("work_orders.empty.title")}</p>
      <p className="mt-1 text-sm text-neutral-600">{filtered ? t("work_orders.no_results.description") : t("work_orders.empty.description")}</p>
      <div className="mt-3 flex justify-center gap-2">
        {filtered ? <Button variant="secondary" onClick={clearFilters}>{t("work_orders.toolbar.clear_filters")}</Button> : null}
        <Button variant="primary" onClick={() => router.push(ROUTES.workOrderNew as Route)}>{t("work_orders.new")}</Button>
      </div>
    </div>
  );

  const statusOptions: CompactOption<DashboardStatusScope>[] = [
    { value: "all", label: t("work_orders.filter.status_all") },
    { value: "active", label: t("work_orders.view.active") },
    { value: "new", label: t("dashboard.status.new") },
    { value: "in_progress", label: t("dashboard.status.in_progress") },
    { value: "completed_unpaid", label: t("dashboard.status.completed_unpaid_short") },
    { value: "completed_paid", label: t("dashboard.status.completed_paid_short") },
    { value: "completed", label: t("work_orders.view.completed") },
    { value: "cancelled", label: t("dashboard.status.cancelled") }
  ];

  const paymentOptions: CompactOption<PaymentScope>[] = [
    { value: "all", label: t("work_orders.filter.payment_all") },
    { value: "unpaid", label: t("work_orders.payment_state.unpaid") },
    { value: "partial", label: t("work_orders.payment_state.partial") },
    { value: "paid", label: t("work_orders.payment_state.paid") }
  ];

  const assigneeOptions: CompactOption<string>[] = [
    { value: "all", label: t("work_orders.filter.assignee_all") },
    { value: "unassigned", label: t("work_orders.unassigned") },
    ...employees.map((employee) => ({
      value: employee.employee_id,
      label: employee.full_name?.trim() || employee.email
    }))
  ];

  const periodOptions: CompactOption<DateScope>[] = [
    { value: "today", label: t("work_orders.period.today") },
    { value: "yesterday", label: t("work_orders.period.yesterday") },
    { value: "7d", label: t("work_orders.period.7d") },
    { value: "30d", label: t("work_orders.period.30d") },
    { value: "this_month", label: t("work_orders.period.this_month") },
    { value: "last_month", label: t("work_orders.period.last_month") },
    { value: "custom", label: t("work_orders.period.custom") }
  ];

  const sortOptions: CompactOption<SortScope>[] = [
    { value: "updated_desc", label: t("work_orders.sort.updated_desc") },
    { value: "created_desc", label: t("work_orders.sort.created_desc") },
    { value: "amount_desc", label: t("work_orders.sort.amount_desc") },
    { value: "amount_asc", label: t("work_orders.sort.amount_asc") },
    { value: "status", label: t("work_orders.sort.status") }
  ];

  const toolbarContent = (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <div className="min-w-[280px] flex-[2_1_420px]">
          <Input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder={t("work_orders.search_full_placeholder")}
            variant="subtle"
            fullHeight="sm"
          />
        </div>

        <CompactFilterMenu
          menuId="status"
          openMenuId={openFilterMenu}
          setOpenMenuId={setOpenFilterMenu}
          className="w-[128px]"
          label={t("work_orders.filter.label.status")}
          value={state.statusScope}
          options={statusOptions}
          active={state.statusScope !== "all"}
          onChange={(next) => applyState({ statusScope: next }, { resetPage: true })}
        />

        <CompactFilterMenu
          menuId="payment"
          openMenuId={openFilterMenu}
          setOpenMenuId={setOpenFilterMenu}
          className="w-[128px]"
          label={t("work_orders.filter.label.payment")}
          value={state.paymentScope}
          options={paymentOptions}
          active={state.paymentScope !== "all"}
          onChange={(next) => applyState({ paymentScope: next }, { resetPage: true })}
        />

        <CompactFilterMenu
          menuId="assignee"
          openMenuId={openFilterMenu}
          setOpenMenuId={setOpenFilterMenu}
          className="w-[148px]"
          label={t("work_orders.filter.label.assignee")}
          value={state.assigneeScope}
          options={assigneeOptions}
          active={state.assigneeScope !== "all"}
          onChange={(next) => applyState({ assigneeScope: next }, { resetPage: true })}
          scrollable
        />

        <CompactFilterMenu
          menuId="period"
          openMenuId={openFilterMenu}
          setOpenMenuId={setOpenFilterMenu}
          className="w-[128px]"
          label={t("work_orders.filter.label.period")}
          value={state.dateScope}
          options={periodOptions}
          active={state.dateScope !== "all" || Boolean(state.dateFrom) || Boolean(state.dateTo)}
          keepOpenValues={["custom"]}
          onChange={(next) => {
            if (next !== "custom") {
              applyState({ dateScope: next, dateFrom: "", dateTo: "" }, { resetPage: true });
              return;
            }
            applyState({ dateScope: "custom" }, { resetPage: true });
          }}
          footer={() =>
            state.dateScope === "custom" ? (
              <div className="space-y-1.5 px-1">
                <p className="text-[11px] text-neutral-500">{t("work_orders.period.custom")}</p>
                <Input
                  type="date"
                  value={state.dateFrom}
                  onChange={(event) => applyState({ dateFrom: event.target.value }, { resetPage: true })}
                  variant="subtle"
                  fullHeight="sm"
                />
                <Input
                  type="date"
                  value={state.dateTo}
                  onChange={(event) => applyState({ dateTo: event.target.value }, { resetPage: true })}
                  variant="subtle"
                  fullHeight="sm"
                />
                <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={() => applyState({ dateScope: "all", dateFrom: "", dateTo: "" }, { resetPage: true })}>
                  {t("work_orders.period.any")}
                </Button>
              </div>
            ) : (
              <button
                type="button"
                className="w-full rounded-lg px-2.5 py-1.5 text-left text-xs text-neutral-700 hover:bg-neutral-100"
                onClick={() => applyState({ dateScope: "all", dateFrom: "", dateTo: "" }, { resetPage: true })}
              >
                {t("work_orders.period.any")}
              </button>
            )
          }
        />

        <CompactFilterMenu
          menuId="sort"
          openMenuId={openFilterMenu}
          setOpenMenuId={setOpenFilterMenu}
          className="w-[132px]"
          label={t("work_orders.filter.label.sort")}
          value={state.sortScope}
          options={sortOptions}
          active={state.sortScope !== "updated_desc"}
          onChange={(next) => applyState({ sortScope: next })}
        />

        {hasAnyFilterActive ? (
          <Button className="h-8 shrink-0 px-2.5 text-neutral-500 hover:text-neutral-700" variant="ghost" onClick={clearFilters}>
            {t("work_orders.toolbar.clear_filters")}
          </Button>
        ) : null}
      </div>
    </div>
  );

  return (
    <PageLayout
      title={t("work_orders.title")}
      subtitle={t("work_orders.subtitle")}
      actions={<Button variant="primary" onClick={() => router.push(ROUTES.workOrderNew as Route)}>{t("work_orders.new")}</Button>}
    >
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-1.5">
          {savedViewOptions.map((view) => (
            <button
              key={view.id}
              type="button"
              onClick={() => applySavedView(view.id)}
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs font-medium transition",
                state.view === view.id
                  ? "border-primary/45 bg-primary/12 text-primary"
                  : "border-neutral-300 bg-neutral-0 text-neutral-700 hover:border-neutral-400 hover:bg-neutral-50"
              )}
            >
              {view.label}
            </button>
          ))}
        </div>

        <div className="hidden md:block">{toolbarContent}</div>

        <div className="md:hidden">
          <div className="flex items-center gap-2">
            <Input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder={t("work_orders.search_full_placeholder")} />
            <Button variant="secondary" onClick={() => setIsMobileFiltersOpen(true)}>
              <Filter className="mr-1 h-4 w-4" />
              {t("work_orders.toolbar.filters")}
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <FilterChip label={t("work_orders.quick.open")} active={state.statusScope === "active"} onClick={() => setQuickToggle("open")} />
          <FilterChip label={t("work_orders.quick.in_progress")} active={state.statusScope === "in_progress"} onClick={() => setQuickToggle("in_progress")} />
          <FilterChip label={t("work_orders.quick.unassigned")} active={state.assigneeScope === "unassigned"} onClick={() => setQuickToggle("unassigned")} />
          <FilterChip label={t("work_orders.quick.unpaid")} active={state.paymentScope === "unpaid"} onClick={() => setQuickToggle("unpaid")} />
          <FilterChip label={t("work_orders.quick.today")} active={state.dateScope === "today"} onClick={() => setQuickToggle("today")} />
        </div>

        <div className="overflow-hidden rounded-md border border-neutral-200 bg-neutral-0">
          <div className="grid grid-cols-2 divide-y divide-neutral-200 sm:grid-cols-3 sm:divide-x sm:divide-y-0 xl:grid-cols-6">
            <TinyMetric label={t("work_orders.kpi.open")} value={metrics.open} tone="warning" />
            <TinyMetric label={t("work_orders.kpi.in_progress")} value={metrics.inProgress} tone="warning" />
            <TinyMetric label={t("work_orders.kpi.completed")} value={metrics.completed} tone="success" />
            <TinyMetric label={t("work_orders.kpi.unpaid")} value={metrics.unpaid} tone="warning" />
            <TinyMetric label={t("work_orders.kpi.total")} value={formatMoney(metrics.revenue)} />
            <TinyMetric label={t("work_orders.kpi.paid")} value={formatMoney(metrics.paid)} tone="success" />
          </div>
        </div>

        {actionError ? <div className="rounded-md border border-error/35 bg-error/10 px-3 py-2 text-sm text-error">{actionError}</div> : null}

        <div className="overflow-visible rounded-lg border border-neutral-200 bg-neutral-0">
          {workOrdersQuery.isLoading ? (
            <SkeletonList />
          ) : workOrdersQuery.error ? (
            <div className="p-3">
              <div className="rounded-md border border-error/35 bg-error/10 p-3">
                <p className="text-sm text-error">{workOrdersQuery.error.message}</p>
                <Button className="mt-2" size="sm" variant="secondary" onClick={() => void workOrdersQuery.refetch()}>{t("datatable.retry")}</Button>
              </div>
            </div>
          ) : pagedRows.length ? (
            <>
              <div className="hidden xl:block">
                <div className="grid grid-cols-[minmax(0,2.2fr)_minmax(0,2.6fr)_minmax(0,1.2fr)_minmax(0,1.7fr)_minmax(0,1.5fr)_minmax(0,1fr)_auto] gap-2 border-b border-neutral-200 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-neutral-500">
                  <div>{t("work_orders.table.order")}</div>
                  <div>{t("work_orders.table.client_vehicle")}</div>
                  <div>{t("work_orders.table.status")}</div>
                  <div>{t("work_orders.table.payment")}</div>
                  <div>{t("work_orders.table.executor")}</div>
                  <div>{t("work_orders.table.total")}</div>
                  <div>{t("work_orders.table.actions")}</div>
                </div>

                {pagedRows.map((row) => {
                  const assignees = row.assigned_employee_ids ?? [];
                  const assigneeLabel = assignees.length
                    ? assignees.map((employeeId) => employeesById.get(employeeId) ?? employeeId).join(", ")
                    : t("work_orders.unassigned");

                  return (
                    <div
                      key={row.id}
                      className="grid cursor-pointer grid-cols-[minmax(0,2.2fr)_minmax(0,2.6fr)_minmax(0,1.2fr)_minmax(0,1.7fr)_minmax(0,1.5fr)_minmax(0,1fr)_auto] gap-2 border-b border-neutral-200 px-3 py-2.5 text-sm last:border-b-0 hover:bg-neutral-50"
                      onClick={() => router.push(ROUTES.workOrderDetail(row.id) as Route)}
                    >
                      <div className="min-w-0">
                        <p className="truncate text-xs font-semibold uppercase tracking-wide text-neutral-500">{t("work_orders.number", { number: row.order_number })}</p>
                        <p className="truncate font-semibold text-primary">{row.description}</p>
                        <p className="mt-0.5 truncate text-xs text-neutral-500">{t("work_orders.created")}: {formatDate(row.created_at)} · {formatDateTime(row.updated_at)}</p>
                      </div>

                      <div className="min-w-0">
                        <p className="truncate font-medium text-neutral-900">{row.client_name?.trim() || t("work_orders.client_fallback")}</p>
                        <p className="truncate text-xs text-neutral-600">{row.vehicle_make_model?.trim() || t("work_orders.vehicle_not_linked")}</p>
                      </div>

                      <div className="min-w-0">
                        <Badge tone={STATUS_BADGE_TONE[row.status]}>{t(`dashboard.status.${row.status}`)}</Badge>
                      </div>

                      <div className="min-w-0">
                        <Badge tone={paymentTone(row.payment_state)}>{paymentStateLabel(row.payment_state, t)}</Badge>
                        <p className="mt-1 text-xs text-neutral-600">{t("work_orders.kpi.paid")}: <span className="font-semibold text-success">{formatMoney(row.paid_amount)}</span></p>
                        <p className="text-xs text-neutral-600">{t("work_orders.kpi.remaining")}: <span className="font-semibold text-warning">{formatMoney(row.remaining_amount)}</span></p>
                      </div>

                      <div className="min-w-0">
                        <p className="truncate text-sm text-neutral-900">{assigneeLabel}</p>
                      </div>

                      <div className="min-w-0">
                        <p className="text-sm font-semibold tabular-nums text-neutral-900">{formatMoney(row.total_amount)}</p>
                      </div>

                      <div className="flex items-center justify-end gap-1" onClick={(event) => event.stopPropagation()}>
                        <Button size="sm" variant="secondary" onClick={() => router.push(ROUTES.workOrderDetail(row.id) as Route)}>{t("common.open")}</Button>
                        <Button size="sm" variant="ghost" onClick={() => router.push(ROUTES.workOrderDetail(row.id) as Route)} title={t("work_orders.action.record_payment")}>
                          <CreditCard className="h-4 w-4" />
                        </Button>
                        <RowActionMenu
                          row={row}
                          t={t}
                          disabled={pendingRowId === row.id}
                          onStatusChange={(nextStatus) => void handleStatusChange(row, nextStatus)}
                          onClose={() => void handleCloseOrder(row)}
                          onOpenDetail={() => router.push(ROUTES.workOrderDetail(row.id) as Route)}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="space-y-1.5 p-2.5 xl:hidden">
                {pagedRows.map((row) => {
                  const assignees = row.assigned_employee_ids ?? [];
                  const assigneeLabel = assignees.length
                    ? assignees.map((employeeId) => employeesById.get(employeeId) ?? employeeId).join(", ")
                    : t("work_orders.unassigned");

                  return (
                    <article
                      key={row.id}
                      className="w-full rounded-md border border-neutral-200 bg-neutral-0 px-2.5 py-2 transition hover:border-neutral-300 hover:bg-neutral-50"
                    >
                      <button
                        type="button"
                        className="w-full text-left"
                        onClick={() => router.push(ROUTES.workOrderDetail(row.id) as Route)}
                      >
                        <div className="flex items-start justify-between gap-2.5">
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-[10px] font-semibold uppercase tracking-wide text-neutral-500">{t("work_orders.number", { number: row.order_number })}</p>
                            <p className="truncate text-sm font-semibold text-primary">{row.description}</p>
                          </div>
                          <div className="shrink-0 text-right">
                            <p className="text-base font-semibold tabular-nums text-neutral-900">{formatMoney(row.total_amount)}</p>
                            <p className="text-[10px] text-neutral-500">{t("work_orders.kpi.total")}</p>
                          </div>
                        </div>

                        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                          <Badge tone={STATUS_BADGE_TONE[row.status]}>{t(`dashboard.status.${row.status}`)}</Badge>
                          <Badge tone={paymentTone(row.payment_state)}>{paymentStateLabel(row.payment_state, t)}</Badge>
                          <span className="text-[11px] text-neutral-500">{formatDateTime(row.updated_at)}</span>
                        </div>

                        <div className="mt-1 space-y-0.5 text-xs text-neutral-600">
                          <p className="truncate">
                            <span className="font-medium text-neutral-800">{row.client_name?.trim() || t("work_orders.client_fallback")}</span>
                            <span className="mx-1 text-neutral-400">•</span>
                            <span>{row.vehicle_make_model?.trim() || t("work_orders.vehicle_not_linked")}</span>
                          </p>
                          <p className="truncate">{t("work_orders.assignee")}: {assigneeLabel}</p>
                          <p className="truncate">
                            {t("work_orders.kpi.paid")}: <span className="font-semibold text-success">{formatMoney(row.paid_amount)}</span>
                            <span className="mx-1.5 text-neutral-400">•</span>
                            {t("work_orders.kpi.remaining")}: <span className="font-semibold text-warning">{formatMoney(row.remaining_amount)}</span>
                          </p>
                        </div>
                      </button>

                      <div className="mt-2 flex items-center gap-1.5 border-t border-neutral-200 pt-2">
                        <Button className="h-8 flex-1" size="sm" variant="primary" onClick={() => router.push(ROUTES.workOrderDetail(row.id) as Route)}>{t("common.open")}</Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-8 w-8 min-w-8 px-0 text-neutral-600"
                          onClick={() => router.push(ROUTES.workOrderDetail(row.id) as Route)}
                          title={t("work_orders.action.record_payment")}
                        >
                          <CreditCard className="h-4 w-4" />
                        </Button>
                        <RowActionMenu
                          row={row}
                          t={t}
                          compact
                          disabled={pendingRowId === row.id}
                          onStatusChange={(nextStatus) => void handleStatusChange(row, nextStatus)}
                          onClose={() => void handleCloseOrder(row)}
                          onOpenDetail={() => router.push(ROUTES.workOrderDetail(row.id) as Route)}
                        />
                      </div>
                    </article>
                  );
                })}
              </div>

              <DesktopPagination page={state.page} total={totalFiltered} onPageChange={(nextPage) => applyState({ page: nextPage }, { keepView: true })} t={t} />
            </>
          ) : (
            <div className="p-3">{renderEmptyState(hasAnyFilterActive)}</div>
          )}
        </div>
      </div>

      <Modal
        open={isMobileFiltersOpen}
        onOpenChange={setIsMobileFiltersOpen}
        title={t("work_orders.toolbar.filters")}
        description={t("work_orders.subtitle")}
        footer={
          <div className="flex justify-end gap-1.5">
            <Button variant="ghost" onClick={clearFilters} disabled={!hasAnyFilterActive}>{t("common.reset")}</Button>
            <Button variant="primary" onClick={() => setIsMobileFiltersOpen(false)}>{t("work_orders.toolbar.apply")}</Button>
          </div>
        }
      >
        <div className="space-y-2">{toolbarContent}</div>
      </Modal>
    </PageLayout>
  );
}
