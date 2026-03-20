"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { formatPhoneForDisplay, normalizePhoneForSubmit } from "@/core/lib/phone";
import { ROUTES } from "@/core/config/routes";
import { cn } from "@/core/lib/utils";
import { DataTable } from "@/design-system/primitives/data-table/data-table";
import type { DataTableColumn } from "@/design-system/primitives/data-table/data-table.types";
import { Badge, Button, Combobox, FormActions, FormField, Input, Modal, PhoneInput, Select, Textarea } from "@/design-system/primitives";
import { PageLayout } from "@/design-system/patterns";
import {
  closeWorkOrder,
  createClient,
  createVehicle,
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
const LOOKUP_LIMIT = 50;

type CreateWorkOrderForm = {
  client_id: string;
  vehicle_id: string;
  assigned_employee_id: string;
  description: string;
  total_amount: string;
};

type IntakeMode = "select" | "create";

type NewClientForm = {
  name: string;
  phone: string;
  email: string;
  comment: string;
};

type NewVehicleForm = {
  plate_number: string;
  make_model: string;
  year: string;
  vin: string;
  comment: string;
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

function defaultNewClientForm(): NewClientForm {
  return {
    name: "",
    phone: "",
    email: "",
    comment: ""
  };
}

function defaultNewVehicleForm(): NewVehicleForm {
  return {
    plate_number: "",
    make_model: "",
    year: "",
    vin: "",
    comment: ""
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
  const [clientMode, setClientMode] = useState<IntakeMode>("select");
  const [vehicleMode, setVehicleMode] = useState<IntakeMode>("select");
  const [clientSearch, setClientSearch] = useState("");
  const [clientLookupQuery, setClientLookupQuery] = useState("");
  const [vehicleSearch, setVehicleSearch] = useState("");
  const [vehicleLookupQuery, setVehicleLookupQuery] = useState("");
  const [newClientForm, setNewClientForm] = useState<NewClientForm>(defaultNewClientForm());
  const [newVehicleForm, setNewVehicleForm] = useState<NewVehicleForm>(defaultNewVehicleForm());
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

  const updateUrlState = useCallback(
    (next: {
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
    },
    [pathname, router, searchParams]
  );

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      const nextQ = search.trim();
      if (nextQ === q) {
        return;
      }

      setQ(nextQ);
      setPage(1);
      updateUrlState({ q: nextQ, page: 1, status: statusFilter, assignee: assigneeFilter });
    }, 250);

    return () => {
      window.clearTimeout(timeout);
    };
  }, [assigneeFilter, q, search, statusFilter, updateUrlState]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setClientLookupQuery(clientSearch.trim());
    }, 200);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [clientSearch]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setVehicleLookupQuery(vehicleSearch.trim());
    }, 200);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [vehicleSearch]);

  const offset = (page - 1) * PAGE_SIZE;
  const workOrdersQuery = useQuery({
    queryKey: mvpQueryKeys.workOrders(q, PAGE_SIZE, offset),
    queryFn: () => fetchWorkOrders({ q, limit: PAGE_SIZE, offset }),
    placeholderData: keepPreviousData
  });

  const clientsQuery = useQuery({
    queryKey: mvpQueryKeys.clients("", LOOKUP_LIMIT, 0),
    queryFn: () => fetchClients({ limit: LOOKUP_LIMIT, offset: 0 })
  });

  const vehiclesQuery = useQuery({
    queryKey: mvpQueryKeys.vehicles("", "", LOOKUP_LIMIT, 0),
    queryFn: () => fetchVehicles({ limit: LOOKUP_LIMIT, offset: 0 })
  });

  const employeesQuery = useQuery({
    queryKey: mvpQueryKeys.employees("", "", LOOKUP_LIMIT, 0),
    queryFn: () => fetchEmployees({ limit: LOOKUP_LIMIT, offset: 0 })
  });

  const clientLookupResultsQuery = useQuery({
    queryKey: mvpQueryKeys.clients(clientLookupQuery, LOOKUP_LIMIT, 0),
    queryFn: () => fetchClients({ q: clientLookupQuery, limit: LOOKUP_LIMIT, offset: 0 }),
    enabled: modalOpen
  });

  const vehiclesByClientQuery = useQuery({
    queryKey: mvpQueryKeys.vehicles(vehicleLookupQuery, form.client_id, LOOKUP_LIMIT, 0),
    queryFn: () =>
      fetchVehicles({
        q: vehicleLookupQuery,
        client_id: form.client_id || undefined,
        limit: LOOKUP_LIMIT,
        offset: 0
      }),
    enabled: modalOpen && Boolean(form.client_id)
  });

  const createMutation = useMutation({
    mutationFn: createWorkOrder,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["work-orders"] });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.dashboardSummary });
    }
  });

  const createClientMutation = useMutation({
    mutationFn: createClient,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["clients"] });
    }
  });

  const createVehicleMutation = useMutation({
    mutationFn: createVehicle,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["vehicles"] });
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

  const clientOptions = useMemo(
    () =>
      (clientLookupResultsQuery.data?.items ?? []).map((client) => ({
        value: client.id,
        label: `${client.name} (${formatPhoneForDisplay(client.phone)})`,
        keywords: [client.phone, client.email ?? ""]
      })),
    [clientLookupResultsQuery.data?.items]
  );

  const vehicleOptions = useMemo(
    () =>
      (vehiclesByClientQuery.data?.items ?? []).map((vehicle) => ({
        value: vehicle.id,
        label: `${vehicle.plate_number} - ${vehicle.make_model}`,
        keywords: [vehicle.vin ?? "", vehicle.make_model]
      })),
    [vehiclesByClientQuery.data?.items]
  );

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
                  onClick={(event) => {
                    event.stopPropagation();
                    router.push(ROUTES.workOrderDetail(row.id) as Route);
                  }}
                  disabled={isRowActionBusy}
                >
                  Open
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
    [clientsById, closeMutation, employeesById, isRowActionBusy, router, statusMutation, vehiclesById]
  );

  const openCreateModal = (): void => {
    router.push(ROUTES.workOrderNew as Route);
  };

  const onCreateClientInline = async (): Promise<void> => {
    const name = newClientForm.name.trim();
    const phone = normalizePhoneForSubmit(newClientForm.phone);
    const email = newClientForm.email.trim();
    const comment = newClientForm.comment.trim();

    if (!name || !phone) {
      setFormError("Client name and phone are required.");
      return;
    }

    setFormError(null);
    const createdClient = await createClientMutation.mutateAsync({
      name,
      phone,
      email: email || null,
      comment: comment || null
    });

    setForm((prev) => ({
      ...prev,
      client_id: createdClient.id,
      vehicle_id: ""
    }));
    setClientMode("select");
    setVehicleMode("create");
    setClientSearch(createdClient.name);
    setVehicleSearch("");
    setNewClientForm(defaultNewClientForm());
  };

  const onCreateVehicleInline = async (): Promise<void> => {
    if (!form.client_id) {
      setFormError("Select or create a client first.");
      return;
    }

    const plateNumber = newVehicleForm.plate_number.trim();
    const makeModel = newVehicleForm.make_model.trim();

    if (!plateNumber || !makeModel) {
      setFormError("Plate number and make/model are required.");
      return;
    }

    const year = newVehicleForm.year.trim();
    const vin = newVehicleForm.vin.trim();
    const comment = newVehicleForm.comment.trim();

    setFormError(null);
    const createdVehicle = await createVehicleMutation.mutateAsync({
      client_id: form.client_id,
      plate_number: plateNumber,
      make_model: makeModel,
      year: year ? Number(year) : null,
      vin: vin || null,
      comment: comment || null
    });

    setForm((prev) => ({
      ...prev,
      vehicle_id: createdVehicle.id
    }));
    setVehicleMode("select");
    setVehicleSearch(createdVehicle.plate_number);
    setNewVehicleForm(defaultNewVehicleForm());
  };

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
    setClientMode("select");
    setVehicleMode("select");
    setClientSearch("");
    setClientLookupQuery("");
    setVehicleSearch("");
    setVehicleLookupQuery("");
    setNewClientForm(defaultNewClientForm());
    setNewVehicleForm(defaultNewVehicleForm());
  };

  const hasActiveSearch = Boolean(q || search);
  const summaryItems: Array<{
    id: string;
    label: string;
    value: string | number;
    tone?: "neutral" | "success" | "warning";
    emphasized?: boolean;
  }> = [
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
            onClick={openCreateModal}
          >
            New work order
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
              placeholder="Search by description, client or vehicle"
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
              Reset
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
          emptyTitle="No work orders in this view"
          emptyDescription="Start with a new work order linked to a client vehicle. It will appear here for assignment and status tracking."
          emptyAction={
            <Button variant="primary" onClick={openCreateModal}>
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

    </PageLayout>
  );
}



