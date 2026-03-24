"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import {
  Badge,
  Button,
  Card,
  FormActions,
  FormField,
  Input,
  Modal,
  Textarea
} from "@/design-system/primitives";
import { PageLayout, Section, StateBoundary } from "@/design-system/patterns";
import {
  addWorkOrderLine,
  assignWorkOrder,
  attachWorkOrderVehicle,
  closeWorkOrder,
  createWorkOrderPayment,
  deleteWorkOrderLine,
  fetchEmployees,
  fetchVehicle,
  fetchVehicles,
  fetchWorkOrder,
  fetchWorkOrderLines,
  fetchWorkOrderPayments,
  fetchWorkOrderTimeline,
  mvpQueryKeys,
  setWorkOrderStatus,
  updateWorkOrderLine
} from "@/features/workspace/api/mvp-api";
import type { WorkOrderOrderLine, WorkOrderStatus } from "@/features/workspace/types/mvp-types";

function formatMoney(value: string): string {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return value;
  }
  return parsed.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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

export function WorkOrderDetailScreen({ workOrderId }: { workOrderId: string }): JSX.Element {
  const queryClient = useQueryClient();
  const [lineModalOpen, setLineModalOpen] = useState(false);
  const [editLineModalOpen, setEditLineModalOpen] = useState(false);
  const [editingLine, setEditingLine] = useState<WorkOrderOrderLine | null>(null);
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [vehicleFilter, setVehicleFilter] = useState("");
  const [employeeFilter, setEmployeeFilter] = useState("");
  const [lineDraft, setLineDraft] = useState({
    line_type: "labor" as "labor" | "part" | "misc",
    name: "",
    quantity: "1",
    unit_price: "",
    comment: ""
  });
  const [editLineDraft, setEditLineDraft] = useState({
    line_type: "labor" as "labor" | "part" | "misc",
    name: "",
    quantity: "1",
    unit_price: "",
    comment: ""
  });
  const [paymentDraft, setPaymentDraft] = useState({
    amount: "",
    method: "cash" as "cash" | "card" | "transfer" | "other",
    comment: ""
  });
  const [lineError, setLineError] = useState<string | null>(null);
  const [editLineError, setEditLineError] = useState<string | null>(null);
  const [paymentError, setPaymentError] = useState<string | null>(null);

  const workOrderQuery = useQuery({
    queryKey: mvpQueryKeys.workOrder(workOrderId),
    queryFn: () => fetchWorkOrder(workOrderId)
  });

  const linesQuery = useQuery({
    queryKey: mvpQueryKeys.workOrderLines(workOrderId),
    queryFn: () => fetchWorkOrderLines(workOrderId)
  });

  const paymentsQuery = useQuery({
    queryKey: mvpQueryKeys.workOrderPayments(workOrderId),
    queryFn: () => fetchWorkOrderPayments(workOrderId)
  });

  const timelineQuery = useQuery({
    queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0),
    queryFn: () => fetchWorkOrderTimeline(workOrderId, { limit: 100, offset: 0 })
  });

  const vehiclesQuery = useQuery({
    queryKey: mvpQueryKeys.vehicles("", "", 300, 0),
    queryFn: () => fetchVehicles({ limit: 300, offset: 0 })
  });

  const employeesQuery = useQuery({
    queryKey: mvpQueryKeys.employees("", "", 200, 0),
    queryFn: () => fetchEmployees({ limit: 200, offset: 0 })
  });

  const employeeById = useMemo(() => {
    const map = new Map<string, string>();
    (employeesQuery.data?.items ?? []).forEach((employee) => {
      map.set(employee.employee_id, `${employee.email} (${employee.role})`);
    });
    return map;
  }, [employeesQuery.data?.items]);

  const attachedVehicleQuery = useQuery({
    queryKey: mvpQueryKeys.vehicle(workOrderQuery.data?.vehicle_id ?? ""),
    queryFn: () => fetchVehicle(workOrderQuery.data!.vehicle_id!),
    enabled: Boolean(workOrderQuery.data?.vehicle_id)
  });

  const statusMutation = useMutation({
    mutationFn: (status: WorkOrderStatus) => setWorkOrderStatus(workOrderId, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: ["work-orders"] });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0) });
    }
  });

  const closeMutation = useMutation({
    mutationFn: () => closeWorkOrder(workOrderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: ["work-orders"] });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0) });
    }
  });

  const attachVehicleMutation = useMutation({
    mutationFn: (vehicleId: string) => attachWorkOrderVehicle(workOrderId, vehicleId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
    }
  });

  const assignMutation = useMutation({
    mutationFn: (employeeId: string | null) => assignWorkOrder(workOrderId, employeeId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: ["work-orders"] });
    }
  });

  const addLineMutation = useMutation({
    mutationFn: addWorkOrderLine.bind(null, workOrderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderLines(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0) });
    }
  });

  const updateLineMutation = useMutation({
    mutationFn: ({
      lineId,
      payload
    }: {
      lineId: string;
      payload: {
        line_type?: "labor" | "part" | "misc";
        name?: string;
        quantity?: number;
        unit_price?: number;
        comment?: string | null;
      };
    }) => updateWorkOrderLine(workOrderId, lineId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderLines(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0) });
    }
  });

  const deleteLineMutation = useMutation({
    mutationFn: (lineId: string) => deleteWorkOrderLine(workOrderId, lineId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderLines(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0) });
    }
  });

  const addPaymentMutation = useMutation({
    mutationFn: createWorkOrderPayment.bind(null, workOrderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderPayments(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0) });
    }
  });

  const openEditLineModal = (line: WorkOrderOrderLine): void => {
    setEditingLine(line);
    setEditLineDraft({
      line_type: line.line_type,
      name: line.name,
      quantity: String(line.quantity),
      unit_price: String(line.unit_price),
      comment: line.comment ?? ""
    });
    setEditLineError(null);
    setEditLineModalOpen(true);
  };

  const filteredVehicles = useMemo(() => {
    const needle = vehicleFilter.trim().toLowerCase();
    if (!needle) {
      return vehiclesQuery.data?.items ?? [];
    }
    return (vehiclesQuery.data?.items ?? []).filter((vehicle) => {
      return (
        vehicle.plate_number.toLowerCase().includes(needle) ||
        vehicle.make_model.toLowerCase().includes(needle) ||
        (vehicle.vin ?? "").toLowerCase().includes(needle)
      );
    });
  }, [vehicleFilter, vehiclesQuery.data?.items]);

  const filteredEmployees = useMemo(() => {
    const needle = employeeFilter.trim().toLowerCase();
    if (!needle) {
      return employeesQuery.data?.items ?? [];
    }
    return (employeesQuery.data?.items ?? []).filter((employee) => {
      return employee.email.toLowerCase().includes(needle) || employee.role.toLowerCase().includes(needle);
    });
  }, [employeeFilter, employeesQuery.data?.items]);

  const currentAssigneeLabel =
    workOrderQuery.data?.assigned_employee_id && employeeById.get(workOrderQuery.data.assigned_employee_id)
      ? employeeById.get(workOrderQuery.data.assigned_employee_id)
      : workOrderQuery.data?.assigned_employee_id
        ? workOrderQuery.data.assigned_employee_id
        : "Unassigned";

  return (
    <PageLayout title="Work-order detail" subtitle={workOrderId}>
      <StateBoundary loading={workOrderQuery.isLoading} error={workOrderQuery.error?.message}>
        {workOrderQuery.data ? (
          <>
            <Section
              title={workOrderQuery.data.description}
              description={`Created ${new Date(workOrderQuery.data.created_at).toLocaleString()}`}
              actions={
                <div className="flex items-center gap-1">
                  <Badge tone={statusTone(workOrderQuery.data.status)}>{statusLabel(workOrderQuery.data.status)}</Badge>
                  <Link href={ROUTES.workOrders}>
                    <Button variant="secondary">Back</Button>
                  </Link>
                </div>
              }
            >
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                <Card className="border-neutral-200 p-2">
                  <p className="text-xs text-neutral-600">Total amount</p>
                  <p className="text-lg font-semibold text-neutral-900">{formatMoney(workOrderQuery.data.total_amount)}</p>
                </Card>
                <Card className="border-neutral-200 p-2">
                  <p className="text-xs text-neutral-600">Remaining amount</p>
                  <p className="text-lg font-semibold text-neutral-900">{formatMoney(workOrderQuery.data.remaining_amount)}</p>
                </Card>
                <Card className="border-neutral-200 p-2">
                  <p className="text-xs text-neutral-600">Paid amount</p>
                  <p className="text-lg font-semibold text-neutral-900">{formatMoney(workOrderQuery.data.paid_amount)}</p>
                </Card>
                <Card className="border-neutral-200 p-2">
                  <p className="text-xs text-neutral-600">Vehicle</p>
                  <p className="text-sm text-neutral-900">
                    {attachedVehicleQuery.data
                      ? `${attachedVehicleQuery.data.plate_number} - ${attachedVehicleQuery.data.make_model}`
                      : workOrderQuery.data.vehicle_id ?? "-"}
                  </p>
                </Card>
              </div>

              <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
                <Card className="border-neutral-200 p-2">
                  <p className="text-xs text-neutral-600">Current assignee</p>
                  <p className="text-sm text-neutral-900">{currentAssigneeLabel}</p>
                </Card>
                <Card className="border-neutral-200 p-2">
                  <p className="text-xs text-neutral-600">Status controls</p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    <Button variant="secondary" size="sm" onClick={() => statusMutation.mutate("in_progress")} disabled={statusMutation.isPending}>
                      Set in progress
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => statusMutation.mutate("completed_unpaid")}
                      disabled={statusMutation.isPending}
                    >
                      Set completed (unpaid)
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => statusMutation.mutate("completed_paid")}
                      disabled={statusMutation.isPending}
                    >
                      Set completed (paid)
                    </Button>
                    <Button variant="destructive" size="sm" onClick={() => statusMutation.mutate("cancelled")} disabled={statusMutation.isPending}>
                      Cancel
                    </Button>
                    <Button size="sm" onClick={() => closeMutation.mutate()} loading={closeMutation.isPending}>
                      Close work order
                    </Button>
                  </div>
                </Card>
              </div>

              <div className="mt-2 flex flex-wrap gap-1">
                <Input
                  placeholder="Find vehicle"
                  value={vehicleFilter}
                  onChange={(event) => setVehicleFilter(event.target.value)}
                />
                <select
                  className="h-5 rounded-sm border border-neutral-300 bg-neutral-0 px-2 text-sm text-neutral-900"
                  defaultValue={workOrderQuery.data.vehicle_id ?? ""}
                  onChange={(event) => {
                    const value = event.target.value;
                    if (!value) {
                      return;
                    }
                    attachVehicleMutation.mutate(value);
                  }}
                >
                  <option value="">Attach vehicle</option>
                  {filteredVehicles.map((vehicle) => (
                    <option key={vehicle.id} value={vehicle.id}>
                      {vehicle.plate_number} - {vehicle.make_model}
                    </option>
                  ))}
                </select>

                <Input
                  placeholder="Find employee"
                  value={employeeFilter}
                  onChange={(event) => setEmployeeFilter(event.target.value)}
                />
                <select
                  className="h-5 rounded-sm border border-neutral-300 bg-neutral-0 px-2 text-sm text-neutral-900"
                  defaultValue={workOrderQuery.data.assigned_employee_id ?? ""}
                  onChange={(event) => {
                    const value = event.target.value || null;
                    assignMutation.mutate(value);
                  }}
                >
                  <option value="">Assign employee</option>
                  {filteredEmployees.map((employee) => (
                    <option key={employee.employee_id} value={employee.employee_id}>
                      {employee.email} ({employee.role})
                    </option>
                  ))}
                </select>
              </div>
            </Section>

            <Section
              title="Order lines"
              description="Line items update total amount and remaining amount"
              actions={
                <Button onClick={() => setLineModalOpen(true)} variant="secondary">
                  Add line
                </Button>
              }
            >
              {linesQuery.isLoading ? (
                <p className="text-sm text-neutral-600">Loading lines...</p>
              ) : linesQuery.error ? (
                <p className="text-sm text-error">{linesQuery.error.message}</p>
              ) : linesQuery.data?.length ? (
                <div className="space-y-1">
                  {linesQuery.data.map((line) => (
                    <Card key={line.id} className="border-neutral-200 p-2">
                      <div className="flex flex-wrap items-start justify-between gap-1">
                        <div>
                          <p className="text-sm font-medium text-neutral-900">
                            {line.name} ({line.line_type})
                          </p>
                          <p className="text-xs text-neutral-600">
                            Qty {line.quantity} x {formatMoney(line.unit_price)} = {formatMoney(line.line_total)}
                          </p>
                        </div>
                        <div className="flex items-center gap-1">
                          <Button variant="secondary" size="sm" onClick={() => openEditLineModal(line)}>
                            Edit
                          </Button>
                          <Button variant="destructive" size="sm" onClick={() => deleteLineMutation.mutate(line.id)}>
                            Remove
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-neutral-600">No lines yet.</p>
              )}
            </Section>

            <Section
              title="Payments"
              description="Payments are independent from work-order closure"
              actions={
                <Button onClick={() => setPaymentModalOpen(true)} variant="secondary">
                  Add payment
                </Button>
              }
            >
              {paymentsQuery.isLoading ? (
                <p className="text-sm text-neutral-600">Loading payments...</p>
              ) : paymentsQuery.error ? (
                <p className="text-sm text-error">{paymentsQuery.error.message}</p>
              ) : paymentsQuery.data?.length ? (
                <div className="space-y-1">
                  {paymentsQuery.data.map((payment) => (
                    <Card key={payment.id} className="border-neutral-200 p-2">
                      <div className="flex flex-wrap items-start justify-between gap-1">
                        <div>
                          <p className="text-sm font-medium text-neutral-900">{formatMoney(payment.amount)}</p>
                          <p className="text-xs text-neutral-600">
                            {payment.method} - {new Date(payment.paid_at).toLocaleString()}
                          </p>
                          {payment.comment ? <p className="text-xs text-neutral-600">{payment.comment}</p> : null}
                        </div>
                        <Badge tone="neutral">Payment</Badge>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-neutral-600">No payments yet.</p>
              )}
            </Section>

            <Section title="Activity timeline" description="Readable history of key work-order changes.">
              {timelineQuery.isLoading ? (
                <p className="text-sm text-neutral-600">Loading activity...</p>
              ) : timelineQuery.error ? (
                <p className="text-sm text-error">{timelineQuery.error.message}</p>
              ) : timelineQuery.data?.length ? (
                <div className="space-y-1">
                  {timelineQuery.data.map((item) => (
                    <Card key={item.id} className="border-neutral-200 p-2">
                      <div className="flex flex-wrap items-start justify-between gap-1">
                        <p className="text-sm text-neutral-900">{item.message}</p>
                        <p className="text-xs text-neutral-500">{new Date(item.created_at).toLocaleString()}</p>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-neutral-600">No activity yet.</p>
              )}
            </Section>
          </>
        ) : null}
      </StateBoundary>

      <Modal
        open={lineModalOpen}
        onOpenChange={(open) => {
          setLineModalOpen(open);
          if (!open) {
            setLineError(null);
          }
        }}
        title="Add order line"
        description="Line items update totals"
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setLineModalOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={async () => {
                const quantity = Number(lineDraft.quantity);
                const unitPrice = Number(lineDraft.unit_price);
                if (!lineDraft.name.trim() || !Number.isFinite(quantity) || !Number.isFinite(unitPrice) || unitPrice <= 0 || quantity <= 0) {
                  setLineError("Line name, quantity and unit price are required.");
                  return;
                }
                setLineError(null);
                await addLineMutation.mutateAsync({
                  line_type: lineDraft.line_type,
                  name: lineDraft.name.trim(),
                  quantity,
                  unit_price: unitPrice,
                  comment: lineDraft.comment.trim() || null
                });
                setLineModalOpen(false);
                setLineDraft({ line_type: "labor", name: "", quantity: "1", unit_price: "", comment: "" });
              }}
              loading={addLineMutation.isPending}
            >
              Add
            </Button>
          </FormActions>
        }
      >
        <div className="space-y-2">
          <FormField id="line-type" label="Type">
            <select
              id="line-type"
              className="h-5 w-full rounded-sm border border-neutral-300 bg-neutral-0 px-2 text-sm text-neutral-900"
              value={lineDraft.line_type}
              onChange={(event) => setLineDraft((prev) => ({ ...prev, line_type: event.target.value as "labor" | "part" | "misc" }))}
            >
              <option value="labor">labor</option>
              <option value="part">part</option>
              <option value="misc">misc</option>
            </select>
          </FormField>
          <FormField id="line-name" label="Name" required>
            <Input id="line-name" value={lineDraft.name} onChange={(event) => setLineDraft((prev) => ({ ...prev, name: event.target.value }))} />
          </FormField>
          <FormField id="line-qty" label="Quantity" required>
            <Input id="line-qty" value={lineDraft.quantity} onChange={(event) => setLineDraft((prev) => ({ ...prev, quantity: event.target.value }))} />
          </FormField>
          <FormField id="line-unit-price" label="Unit price" required>
            <Input
              id="line-unit-price"
              value={lineDraft.unit_price}
              onChange={(event) => setLineDraft((prev) => ({ ...prev, unit_price: event.target.value }))}
            />
          </FormField>
          <FormField id="line-comment" label="Comment">
            <Textarea
              id="line-comment"
              value={lineDraft.comment}
              onChange={(event) => setLineDraft((prev) => ({ ...prev, comment: event.target.value }))}
            />
          </FormField>
          {lineError ? <p className="text-sm text-error">{lineError}</p> : null}
        </div>
      </Modal>

      <Modal
        open={editLineModalOpen}
        onOpenChange={(open) => {
          setEditLineModalOpen(open);
          if (!open) {
            setEditingLine(null);
            setEditLineError(null);
          }
        }}
        title="Edit order line"
        description={editingLine ? `Line ${editingLine.name}` : "Edit line fields"}
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setEditLineModalOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={async () => {
                if (!editingLine) {
                  return;
                }
                const quantity = Number(editLineDraft.quantity);
                const unitPrice = Number(editLineDraft.unit_price);
                if (!editLineDraft.name.trim() || !Number.isFinite(quantity) || !Number.isFinite(unitPrice) || unitPrice <= 0 || quantity <= 0) {
                  setEditLineError("Line name, quantity and unit price are required.");
                  return;
                }
                setEditLineError(null);
                await updateLineMutation.mutateAsync({
                  lineId: editingLine.id,
                  payload: {
                    line_type: editLineDraft.line_type,
                    name: editLineDraft.name.trim(),
                    quantity,
                    unit_price: unitPrice,
                    comment: editLineDraft.comment.trim() || null
                  }
                });
                setEditLineModalOpen(false);
                setEditingLine(null);
              }}
              loading={updateLineMutation.isPending}
            >
              Save
            </Button>
          </FormActions>
        }
      >
        <div className="space-y-2">
          <FormField id="edit-line-type" label="Type">
            <select
              id="edit-line-type"
              className="h-5 w-full rounded-sm border border-neutral-300 bg-neutral-0 px-2 text-sm text-neutral-900"
              value={editLineDraft.line_type}
              onChange={(event) => setEditLineDraft((prev) => ({ ...prev, line_type: event.target.value as "labor" | "part" | "misc" }))}
            >
              <option value="labor">labor</option>
              <option value="part">part</option>
              <option value="misc">misc</option>
            </select>
          </FormField>
          <FormField id="edit-line-name" label="Name" required>
            <Input
              id="edit-line-name"
              value={editLineDraft.name}
              onChange={(event) => setEditLineDraft((prev) => ({ ...prev, name: event.target.value }))}
            />
          </FormField>
          <FormField id="edit-line-qty" label="Quantity" required>
            <Input
              id="edit-line-qty"
              value={editLineDraft.quantity}
              onChange={(event) => setEditLineDraft((prev) => ({ ...prev, quantity: event.target.value }))}
            />
          </FormField>
          <FormField id="edit-line-unit-price" label="Unit price" required>
            <Input
              id="edit-line-unit-price"
              value={editLineDraft.unit_price}
              onChange={(event) => setEditLineDraft((prev) => ({ ...prev, unit_price: event.target.value }))}
            />
          </FormField>
          <FormField id="edit-line-comment" label="Comment">
            <Textarea
              id="edit-line-comment"
              value={editLineDraft.comment}
              onChange={(event) => setEditLineDraft((prev) => ({ ...prev, comment: event.target.value }))}
            />
          </FormField>
          {editLineError ? <p className="text-sm text-error">{editLineError}</p> : null}
        </div>
      </Modal>

      <Modal
        open={paymentModalOpen}
        onOpenChange={(open) => {
          setPaymentModalOpen(open);
          if (!open) {
            setPaymentError(null);
          }
        }}
        title="Add payment"
        description="Payment does not close work order automatically"
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setPaymentModalOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={async () => {
                const amount = Number(paymentDraft.amount);
                if (!Number.isFinite(amount) || amount <= 0) {
                  setPaymentError("Payment amount must be greater than 0.");
                  return;
                }
                setPaymentError(null);
                await addPaymentMutation.mutateAsync({
                  amount,
                  method: paymentDraft.method,
                  comment: paymentDraft.comment.trim() || null
                });
                setPaymentModalOpen(false);
                setPaymentDraft({ amount: "", method: "cash", comment: "" });
              }}
              loading={addPaymentMutation.isPending}
            >
              Add payment
            </Button>
          </FormActions>
        }
      >
        <div className="space-y-2">
          <FormField id="payment-amount" label="Amount" required>
            <Input
              id="payment-amount"
              value={paymentDraft.amount}
              onChange={(event) => setPaymentDraft((prev) => ({ ...prev, amount: event.target.value }))}
            />
          </FormField>
          <FormField id="payment-method" label="Method" required>
            <select
              id="payment-method"
              className="h-5 w-full rounded-sm border border-neutral-300 bg-neutral-0 px-2 text-sm text-neutral-900"
              value={paymentDraft.method}
              onChange={(event) =>
                setPaymentDraft((prev) => ({ ...prev, method: event.target.value as "cash" | "card" | "transfer" | "other" }))
              }
            >
              <option value="cash">cash</option>
              <option value="card">card</option>
              <option value="transfer">transfer</option>
              <option value="other">other</option>
            </select>
          </FormField>
          <FormField id="payment-comment" label="Comment">
            <Textarea
              id="payment-comment"
              value={paymentDraft.comment}
              onChange={(event) => setPaymentDraft((prev) => ({ ...prev, comment: event.target.value }))}
            />
          </FormField>
          {paymentError ? <p className="text-sm text-error">{paymentError}</p> : null}
        </div>
      </Modal>
    </PageLayout>
  );
}
