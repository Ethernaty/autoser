"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { formatPhoneForDisplay } from "@/core/lib/phone";
import { ROUTES } from "@/core/config/routes";
import { cn } from "@/core/lib/utils";
import { DataTable } from "@/design-system/primitives/data-table/data-table";
import type { DataTableColumn } from "@/design-system/primitives/data-table/data-table.types";
import { Badge, Button, FormActions, FormField, Input, Modal, Select, Textarea } from "@/design-system/primitives";
import { PageLayout } from "@/design-system/patterns";
import {
  closeWorkOrder,
  createWorkOrder,
  fetchClients,
  fetchEmployees,
  fetchVehicles,
  fetchWorkOrders,
  mvpQueryKeys,
  setWorkOrderStatus
} from "@/features/workspace/api/mvp-api";
import type { WorkOrderRecord, WorkOrderStatus } from "@/features/workspace/types/mvp-types";

const PAGE_SIZE = 20;

type CreateWorkOrderForm = {
  client_id: string;
  vehicle_id: string;
  assigned_employee_id: string;
  description: string;
  total_amount: string;
};

function defaultForm(): CreateWorkOrderForm {
  return {
    client_id: "",
    vehicle_id: "",
    assigned_employee_id: "",
    description: "",
    total_amount: ""
  };
}

const STATUS_META: Record<WorkOrderStatus, { label: string; tone: "neutral" | "warning" | "success" | "error" }> = {
  new: { label: "New", tone: "neutral" },
  in_progress: { label: "In progress", tone: "warning" },
  completed: { label: "Completed", tone: "success" },
  canceled: { label: "Canceled", tone: "error" }
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
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const initialQ = searchParams.get("q") ?? "";
  const initialPageRaw = Number(searchParams.get("page") ?? "1");
  const initialPage = Number.isFinite(initialPageRaw) && initialPageRaw > 0 ? initialPageRaw : 1;
  const initialStatus = (searchParams.get("status") as WorkOrderStatus | null) ?? "all";
  const isInitialStatusValid = initialStatus === "all" || Object.prototype.hasOwnProperty.call(STATUS_META, initialStatus);
  const initialAssignee = searchParams.get("assignee") ?? "all";

  const [q, setQ] = useState(initialQ);
  const [search, setSearch] = useState(initialQ);
  const [page, setPage] = useState(initialPage);
  const [statusFilter, setStatusFilter] = useState<"all" | WorkOrderStatus>(isInitialStatusValid ? initialStatus : "all");
  const [assigneeFilter, setAssigneeFilter] = useState<"all" | "unassigned" | string>(initialAssignee);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<CreateWorkOrderForm>(defaultForm());
  const [clientSearch, setClientSearch] = useState("");
  const [vehicleSearch, setVehicleSearch] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    const nextQ = searchParams.get("q") ?? "";
    const nextPageRaw = Number(searchParams.get("page") ?? "1");
    const nextPage = Number.isFinite(nextPageRaw) && nextPageRaw > 0 ? nextPageRaw : 1;
    const nextStatusRaw = (searchParams.get("status") as WorkOrderStatus | null) ?? "all";
    const nextStatus =
      nextStatusRaw === "all" || Object.prototype.hasOwnProperty.call(STATUS_META, nextStatusRaw) ? nextStatusRaw : "all";
    const nextAssignee = searchParams.get("assignee") ?? "all";

    setQ(nextQ);
    setSearch(nextQ);
    setPage(nextPage);
    setStatusFilter(nextStatus);
    setAssigneeFilter(nextAssignee);
  }, [searchParams]);

  const updateUrlState = (next: {
    q: string;
    page: number;
    status: "all" | WorkOrderStatus;
    assignee: "all" | "unassigned" | string;
  }): void => {
    const params = new URLSearchParams(searchParams.toString());

    if (next.q) {
      params.set("q", next.q);
    } else {
      params.delete("q");
    }

    if (next.page > 1) {
      params.set("page", String(next.page));
    } else {
      params.delete("page");
    }

    if (next.status !== "all") {
      params.set("status", next.status);
    } else {
      params.delete("status");
    }

    if (next.assignee !== "all") {
      params.set("assignee", next.assignee);
    } else {
      params.delete("assignee");
    }

    const queryString = params.toString();
    const nextHref = queryString ? `${pathname}?${queryString}` : pathname;
    router.replace(nextHref as Route, { scroll: false });
  };

  const offset = (page - 1) * PAGE_SIZE;
  const workOrdersQuery = useQuery({
    queryKey: mvpQueryKeys.workOrders(q, PAGE_SIZE, offset),
    queryFn: () => fetchWorkOrders({ q, limit: PAGE_SIZE, offset }),
    placeholderData: keepPreviousData
  });

  const clientsQuery = useQuery({
    queryKey: mvpQueryKeys.clients("", 300, 0),
    queryFn: () => fetchClients({ limit: 300, offset: 0 })
  });

  const vehiclesQuery = useQuery({
    queryKey: mvpQueryKeys.vehicles("", "", 500, 0),
    queryFn: () => fetchVehicles({ limit: 500, offset: 0 })
  });

  const employeesQuery = useQuery({
    queryKey: mvpQueryKeys.employees("", "", 200, 0),
    queryFn: () => fetchEmployees({ limit: 200, offset: 0 })
  });

  const createMutation = useMutation({
    mutationFn: createWorkOrder,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["work-orders"] });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.dashboardSummary });
    }
  });

  const statusMutation = useMutation({
    mutationFn: ({ workOrderId, status }: { workOrderId: string; status: "new" | "in_progress" | "completed" | "canceled" }) =>
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

  const employeesById = useMemo(() => {
    const map = new Map<string, string>();
    (employeesQuery.data?.items ?? []).forEach((employee) => map.set(employee.employee_id, employee.email));
    return map;
  }, [employeesQuery.data?.items]);

  const filteredClients = useMemo(() => {
    const normalized = clientSearch.trim().toLowerCase();
    if (!normalized) {
      return clientsQuery.data?.items ?? [];
    }
    return (clientsQuery.data?.items ?? []).filter((client) => {
      return (
        client.name.toLowerCase().includes(normalized) ||
        client.phone.toLowerCase().includes(normalized) ||
        (client.email ?? "").toLowerCase().includes(normalized)
      );
    });
  }, [clientSearch, clientsQuery.data?.items]);

  const filteredVehicles = useMemo(() => {
    const normalizedVehicleSearch = vehicleSearch.trim().toLowerCase();
    return (vehiclesQuery.data?.items ?? []).filter((vehicle) => {
      const belongsToClient = !form.client_id || vehicle.client_id === form.client_id;
      const matchesSearch =
        !normalizedVehicleSearch ||
        vehicle.plate_number.toLowerCase().includes(normalizedVehicleSearch) ||
        vehicle.make_model.toLowerCase().includes(normalizedVehicleSearch) ||
        (vehicle.vin ?? "").toLowerCase().includes(normalizedVehicleSearch);
      return belongsToClient && matchesSearch;
    });
  }, [form.client_id, vehicleSearch, vehiclesQuery.data?.items]);

  useEffect(() => {
    if (!form.vehicle_id) {
      return;
    }
    const stillExists = filteredVehicles.some((vehicle) => vehicle.id === form.vehicle_id);
    if (!stillExists) {
      setForm((prev) => ({ ...prev, vehicle_id: "" }));
    }
  }, [filteredVehicles, form.vehicle_id]);

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

  const queueStats = useMemo(() => {
    const openCount = filteredRows.filter((row) => row.status === "new" || row.status === "in_progress").length;
    const completedCount = filteredRows.filter((row) => row.status === "completed").length;
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

    return {
      totalAmount,
      paidAmount,
      remainingAmount
    };
  }, [filteredRows]);
  const isRowActionBusy = statusMutation.isPending || closeMutation.isPending;

  const columns = useMemo<DataTableColumn<WorkOrderRecord>[]>(
    () => [
      {
        id: "queue",
        header: "Queue item",
        cell: (row) => (
          <div className="space-y-1">
            <Link href={ROUTES.workOrderDetail(row.id) as Route} className="block truncate font-semibold text-primary hover:underline">
              {row.description}
            </Link>
            <p className="text-xs text-neutral-500">
              #{row.id.slice(0, 8)} - Created {formatDateTime(row.created_at)}
            </p>
          </div>
        )
      },
      {
        id: "party",
        header: "Client / vehicle",
        cell: (row) => (
          <div className="space-y-1">
            <p className="truncate font-medium text-neutral-900">{clientsById.get(row.client_id) ?? row.client_id}</p>
            <p className="truncate text-xs text-neutral-600">{row.vehicle_id ? vehiclesById.get(row.vehicle_id) ?? row.vehicle_id : "Vehicle not linked"}</p>
          </div>
        )
      },
      {
        id: "money",
        header: "Financials",
        align: "right",
        cell: (row) => {
          const remaining = parseMoney(row.remaining_amount);
          return (
            <div className="ml-auto w-full max-w-[210px] space-y-1">
              <p className="flex items-center justify-between text-xs text-neutral-600">
                <span>Total</span>
                <span className="font-semibold tabular-nums text-neutral-900">{formatMoney(row.total_amount)}</span>
              </p>
              <p className="flex items-center justify-between text-xs text-neutral-600">
                <span>Paid</span>
                <span className="font-semibold tabular-nums text-success">{formatMoney(row.paid_amount)}</span>
              </p>
              <p className="flex items-center justify-between text-xs text-neutral-600">
                <span>Remaining</span>
                <span className={cn("font-semibold tabular-nums", remaining > 0 ? "text-warning" : "text-success")}>
                  {formatMoney(row.remaining_amount)}
                </span>
              </p>
            </div>
          );
        }
      },
      {
        id: "ops",
        header: "Status / actions",
        cell: (row) => {
          const transition =
            row.status === "new"
              ? {
                  label: "Start",
                  onClick: () => statusMutation.mutate({ workOrderId: row.id, status: "in_progress" }),
                  variant: "primary" as const
                }
              : row.status === "in_progress"
                ? {
                    label: "Complete",
                    onClick: () => statusMutation.mutate({ workOrderId: row.id, status: "completed" }),
                    variant: "primary" as const
                  }
                : row.status === "completed"
                  ? {
                      label: "Close",
                      onClick: () => closeMutation.mutate(row.id),
                      variant: "secondary" as const
                    }
                  : null;

          return (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="space-y-1">
                <Badge tone={STATUS_META[row.status].tone}>{STATUS_META[row.status].label}</Badge>
                <p className="text-xs text-neutral-600">
                  {row.assigned_employee_id ? (
                    <>Assignee: {employeesById.get(row.assigned_employee_id) ?? row.assigned_employee_id}</>
                  ) : (
                    "Assignee: Unassigned"
                  )}
                </p>
              </div>
              <div className="flex items-center gap-1.5">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    router.push(ROUTES.workOrderDetail(row.id) as Route);
                  }}
                  disabled={isRowActionBusy}
                >
                  Open
                </Button>
                {transition ? (
                  <Button size="sm" variant={transition.variant} onClick={transition.onClick} disabled={isRowActionBusy}>
                    {transition.label}
                  </Button>
                ) : null}
              </div>
            </div>
          );
        }
      }
    ],
    [clientsById, closeMutation, employeesById, isRowActionBusy, router, statusMutation, vehiclesById]
  );

  const onSubmitCreate = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!form.client_id || !form.vehicle_id || !form.description.trim()) {
      setFormError("Client, vehicle and description are required.");
      return;
    }

    const total = Number(form.total_amount);
    if (!Number.isFinite(total) || total <= 0) {
      setFormError("Total amount must be greater than 0.");
      return;
    }

    setFormError(null);
    await createMutation.mutateAsync({
      client_id: form.client_id,
      vehicle_id: form.vehicle_id,
      description: form.description.trim(),
      total_amount: total,
      assigned_employee_id: form.assigned_employee_id || null,
      status: "new"
    });

    setModalOpen(false);
    setForm(defaultForm());
    setClientSearch("");
    setVehicleSearch("");
  };

  const hasActiveSearch = Boolean(q || search);
  const totalRecords = workOrdersQuery.data?.total ?? 0;
  const summaryItems: Array<{
    id: string;
    label: string;
    value: string | number;
    tone?: "neutral" | "success" | "warning";
    emphasized?: boolean;
  }> = [
    { id: "visible", label: "Visible in queue", value: filteredRows.length },
    { id: "open", label: "Open queue", value: queueStats.openCount, tone: "warning" },
    { id: "completed", label: "Completed", value: queueStats.completedCount, tone: "success" },
    { id: "unassigned", label: "Unassigned", value: queueStats.unassignedCount, tone: "neutral" },
    { id: "total", label: "Total amount", value: formatMoney(String(totals.totalAmount)), emphasized: true },
    { id: "paid", label: "Paid", value: formatMoney(String(totals.paidAmount)), tone: "success", emphasized: true },
    {
      id: "remaining",
      label: "Remaining",
      value: formatMoney(String(totals.remainingAmount)),
      tone: totals.remainingAmount > 0 ? "warning" : "success",
      emphasized: true
    }
  ];

  return (
    <PageLayout
      title="Work orders"
      subtitle="Daily service queue with assignment, status control and payment visibility."
      actions={
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => void workOrdersQuery.refetch()} disabled={workOrdersQuery.isFetching}>
            Refresh
          </Button>
          <Button
            variant="primary"
            onClick={() => {
              setForm(defaultForm());
              setClientSearch("");
              setVehicleSearch("");
              setFormError(null);
              setModalOpen(true);
            }}
          >
            New work order
          </Button>
        </div>
      }
    >
      <div className="overflow-hidden rounded-lg border border-neutral-300 bg-neutral-0 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-200 px-4 py-3">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Queue controls</p>
            <p className="mt-1 text-sm text-neutral-700">Search and filter first, then perform status transitions directly in queue rows.</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone="neutral">Server total {totalRecords}</Badge>
            <Badge tone="primary">Visible {filteredRows.length}</Badge>
          </div>
        </div>

        <div className="px-4 py-3">
          <div className="grid grid-cols-1 gap-2 xl:grid-cols-[minmax(0,1fr)_220px_240px_auto]">
            <form
              className="flex w-full gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                const nextQ = search.trim();
                setQ(nextQ);
                setPage(1);
                updateUrlState({ q: nextQ, page: 1, status: statusFilter, assignee: assigneeFilter });
              }}
            >
              <Input
                className="w-full"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search by work-order description"
              />
              <Button type="submit" variant="secondary">
                Search
              </Button>
            </form>

            <Select
              value={statusFilter}
              onChange={(event) => {
                const nextStatus = event.target.value as "all" | WorkOrderStatus;
                setStatusFilter(nextStatus);
                setPage(1);
                updateUrlState({ q, page: 1, status: nextStatus, assignee: assigneeFilter });
              }}
            >
              <option value="all">All statuses</option>
              <option value="new">New</option>
              <option value="in_progress">In progress</option>
              <option value="completed">Completed</option>
              <option value="canceled">Canceled</option>
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
              <option value="all">All assignees</option>
              <option value="unassigned">Unassigned</option>
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
              Reset all
            </Button>
          </div>
        </div>

        <div className="border-t border-neutral-200 bg-neutral-50 px-4 py-3">
          <div className="grid grid-cols-2 gap-x-3 gap-y-3 md:grid-cols-4 xl:grid-cols-7 xl:gap-x-0">
            {summaryItems.map((item, index) => (
              <div
                key={item.id}
                className={cn(
                  "min-w-0 xl:px-4",
                  index === 0 ? "xl:pl-0" : "xl:border-l xl:border-neutral-200",
                  index === summaryItems.length - 1 ? "xl:pr-0" : ""
                )}
              >
                <SummaryMetric label={item.label} value={item.value} tone={item.tone} emphasized={item.emphasized} />
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-[18px] leading-6 font-semibold text-neutral-900">Work-order queue</h2>
            <p className="mt-1 text-sm text-neutral-600">Primary operational list for assignment, cash control and closure decisions.</p>
          </div>
        </div>
        <DataTable
          columns={columns}
          rows={filteredRows}
          getRowId={(row) => row.id}
          loading={workOrdersQuery.isLoading}
          error={workOrdersQuery.error?.message}
          onRetry={() => void workOrdersQuery.refetch()}
          emptyTitle="No work orders in this view"
          emptyDescription="Start with a new work order linked to a client vehicle. It will appear here for assignment and status tracking."
          emptyAction={
            <Button
              variant="primary"
              onClick={() => {
                setForm(defaultForm());
                setClientSearch("");
                setVehicleSearch("");
                setFormError(null);
                setModalOpen(true);
              }}
            >
              Create work order
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

      <Modal
        open={modalOpen}
        onOpenChange={setModalOpen}
        title="Create work order"
        description="Use canonical flow: client -> vehicle -> assignee -> amount."
        size="lg"
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="work-order-create-form" loading={createMutation.isPending}>
              Create
            </Button>
          </FormActions>
        }
      >
        <form id="work-order-create-form" className="grid grid-cols-1 gap-3 md:grid-cols-2" onSubmit={(event) => void onSubmitCreate(event)}>
          <FormField id="client-search" label="Find client">
            <Input
              id="client-search"
              value={clientSearch}
              onChange={(event) => setClientSearch(event.target.value)}
              placeholder="Search client by name, phone, email"
            />
          </FormField>
          <FormField id="client_id" label="Client" required>
            <Select
              id="client_id"
              value={form.client_id}
              onChange={(event) => setForm((prev) => ({ ...prev, client_id: event.target.value }))}
            >
              <option value="">Select client</option>
              {filteredClients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name} ({formatPhoneForDisplay(client.phone)})
                </option>
              ))}
            </Select>
          </FormField>

          <FormField id="vehicle-search" label="Find vehicle">
            <Input
              id="vehicle-search"
              value={vehicleSearch}
              onChange={(event) => setVehicleSearch(event.target.value)}
              placeholder="Search by plate, model, VIN"
            />
          </FormField>
          <FormField id="vehicle_id" label="Vehicle" required>
            <Select
              id="vehicle_id"
              value={form.vehicle_id}
              onChange={(event) => setForm((prev) => ({ ...prev, vehicle_id: event.target.value }))}
            >
              <option value="">Select vehicle</option>
              {filteredVehicles.map((vehicle) => (
                <option key={vehicle.id} value={vehicle.id}>
                  {vehicle.plate_number} - {vehicle.make_model}
                </option>
              ))}
            </Select>
          </FormField>
          {form.client_id && filteredVehicles.length === 0 ? (
            <p className="text-xs text-neutral-600 md:col-span-2">No vehicles found for selected client. Add a vehicle first.</p>
          ) : null}

          <FormField id="assigned_employee_id" label="Assignee (optional)" className="md:col-span-2">
            <Select
              id="assigned_employee_id"
              value={form.assigned_employee_id}
              onChange={(event) => setForm((prev) => ({ ...prev, assigned_employee_id: event.target.value }))}
            >
              <option value="">Unassigned</option>
              {(employeesQuery.data?.items ?? []).map((employee) => (
                <option key={employee.employee_id} value={employee.employee_id}>
                  {employee.email} ({employee.role})
                </option>
              ))}
            </Select>
          </FormField>

          <FormField id="total_amount" label="Total amount" required>
            <Input
              id="total_amount"
              value={form.total_amount}
              onChange={(event) => setForm((prev) => ({ ...prev, total_amount: event.target.value }))}
              placeholder="0.00"
            />
          </FormField>
          <FormField id="description" label="Description" required>
            <Textarea
              className="min-h-28"
              id="description"
              value={form.description}
              onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
            />
          </FormField>

          {formError ? <p className="text-sm text-error md:col-span-2">{formError}</p> : null}
          {createMutation.error ? <p className="text-sm text-error md:col-span-2">{createMutation.error.message}</p> : null}
        </form>
      </Modal>
    </PageLayout>
  );
}



