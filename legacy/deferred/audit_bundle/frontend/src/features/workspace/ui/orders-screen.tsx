"use client";

import { Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";

import { DataTable } from "@/design-system/primitives/data-table/data-table";
import type { DataTableColumn } from "@/design-system/primitives/data-table/data-table.types";
import { Badge, Button, ConfirmDialog, FormActions, FormField, FormSection, Input, Modal, Textarea } from "@/design-system/primitives";
import { PageLayout, Section, Toolbar } from "@/design-system/patterns";
import { useAccess } from "@/features/access/hooks/use-access";
import { DisableIfNoAccess } from "@/features/access/ui/access-guard";
import {
  useChangeOrderStatusMutation,
  useCreateWorkflowOrderMutation,
  usePayOrderMutation,
  useUpdateOrderMutation,
  useWorkspaceOrdersQuery
} from "@/features/workspace/hooks";
import { OrderStatusBadge } from "@/features/workspace/ui/order-status-badge";
import type { OrderRecord, OrderStatus } from "@/features/workspace/types";

const PAGE_SIZE = 20;

type CreateOrderFormState = {
  phone: string;
  clientName: string;
  description: string;
  price: string;
};

type EditOrderFormState = {
  description: string;
  price: string;
  status: OrderStatus;
};

function defaultCreateOrderForm(): CreateOrderFormState {
  return {
    phone: "",
    clientName: "",
    description: "",
    price: ""
  };
}

function defaultEditOrderForm(): EditOrderFormState {
  return {
    description: "",
    price: "",
    status: "new"
  };
}

function validateCreateOrder(state: CreateOrderFormState): Record<string, string> {
  const errors: Record<string, string> = {};

  if (!state.phone.trim()) {
    errors.phone = "Phone is required";
  }

  if (!state.description.trim()) {
    errors.description = "Description is required";
  }

  const price = Number(state.price);
  if (!Number.isFinite(price) || price <= 0) {
    errors.price = "Price must be greater than 0";
  }

  return errors;
}

function validateEditOrder(state: EditOrderFormState): Record<string, string> {
  const errors: Record<string, string> = {};

  if (!state.description.trim()) {
    errors.description = "Description is required";
  }

  const price = Number(state.price);
  if (!Number.isFinite(price) || price <= 0) {
    errors.price = "Price must be greater than 0";
  }

  return errors;
}

export function OrdersScreen(): JSX.Element {
  const { canAccess } = useAccess();

  const [searchInput, setSearchInput] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createForm, setCreateForm] = useState<CreateOrderFormState>(defaultCreateOrderForm());
  const [createErrors, setCreateErrors] = useState<Record<string, string>>({});

  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editForm, setEditForm] = useState<EditOrderFormState>(defaultEditOrderForm());
  const [editErrors, setEditErrors] = useState<Record<string, string>>({});
  const [editingOrder, setEditingOrder] = useState<OrderRecord | null>(null);

  const [cancelOrderId, setCancelOrderId] = useState<string | null>(null);

  const createMutation = useCreateWorkflowOrderMutation();
  const updateMutation = useUpdateOrderMutation();
  const statusMutation = useChangeOrderStatusMutation();
  const payMutation = usePayOrderMutation();

  const offset = (page - 1) * PAGE_SIZE;
  const ordersQuery = useWorkspaceOrdersQuery({ q: query, limit: PAGE_SIZE, offset });

  const rows = ordersQuery.data?.items ?? [];

  const columns = useMemo<DataTableColumn<OrderRecord>[]>(
    () => [
      {
        id: "client",
        header: "Client",
        minWidth: 180,
        cell: (row) => <span className="font-medium text-neutral-900">{row.client_name ?? row.client_id.slice(0, 8)}</span>
      },
      {
        id: "description",
        header: "Description",
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
        header: "Price",
        minWidth: 120,
        align: "right",
        cell: (row) => <span className="font-medium text-neutral-900">{row.price}</span>
      },
      {
        id: "created",
        header: "Created",
        minWidth: 180,
        align: "right",
        cell: (row) => new Date(row.created_at).toLocaleString()
      }
    ],
    []
  );

  const onToggleRow = (rowId: string): void => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(rowId)) {
        next.delete(rowId);
      } else {
        next.add(rowId);
      }
      return next;
    });
  };

  const onToggleAllRows = (rowIds: string[], checked: boolean): void => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        rowIds.forEach((rowId) => next.add(rowId));
      } else {
        rowIds.forEach((rowId) => next.delete(rowId));
      }
      return next;
    });
  };

  const openCreateModal = (): void => {
    setCreateForm(defaultCreateOrderForm());
    setCreateErrors({});
    setCreateModalOpen(true);
  };

  const openEditModal = (order: OrderRecord): void => {
    setEditingOrder(order);
    setEditForm({
      description: order.description,
      price: String(order.price),
      status: order.status
    });
    setEditErrors({});
    setEditModalOpen(true);
  };

  const submitCreateOrder = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();

    const errors = validateCreateOrder(createForm);
    setCreateErrors(errors);

    if (Object.keys(errors).length > 0) {
      return;
    }

    await createMutation.mutateAsync({
      phone: createForm.phone.trim(),
      clientName: createForm.clientName.trim() || undefined,
      description: createForm.description.trim(),
      price: Number(createForm.price)
    });

    setCreateModalOpen(false);
    setCreateForm(defaultCreateOrderForm());
  };

  const submitEditOrder = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();

    if (!editingOrder) {
      return;
    }

    const errors = validateEditOrder(editForm);
    setEditErrors(errors);

    if (Object.keys(errors).length > 0) {
      return;
    }

    await updateMutation.mutateAsync({
      orderId: editingOrder.id,
      description: editForm.description.trim(),
      price: Number(editForm.price),
      status: editForm.status
    });

    setEditModalOpen(false);
    setEditingOrder(null);
    setEditForm(defaultEditOrderForm());
  };

  const createError = createMutation.error?.message ?? null;
  const editError = updateMutation.error?.message ?? null;

  return (
    <PageLayout title="Orders" subtitle="Dense operational queue for daily workflow">
      <Section>
        <Toolbar
          leading={
            <form
              className="flex flex-wrap items-center gap-1"
              onSubmit={(event) => {
                event.preventDefault();
                setQuery(searchInput.trim());
                setPage(1);
              }}
            >
              <div className="relative min-w-[280px]">
                <Search className="pointer-events-none absolute left-1 top-1.5 h-2.5 w-2.5 text-neutral-500" />
                <Input
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  placeholder="Search by description"
                  className="pl-4"
                />
              </div>
              <Button type="submit" variant="secondary">
                Search
              </Button>
              {query ? (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setSearchInput("");
                    setQuery("");
                    setPage(1);
                  }}
                >
                  Reset
                </Button>
              ) : null}
            </form>
          }
          trailing={
            <DisableIfNoAccess permission="orders.create" limitType="maxOrdersPerMonth" increment={1}>
              {(disabled, onUpgrade) => (
                <div className="flex items-center gap-1">
                  <Button variant="primary" disabled={disabled} onClick={openCreateModal}>
                    <Plus className="h-2.5 w-2.5" />
                    New order
                  </Button>
                  {disabled ? (
                    <Button variant="secondary" onClick={onUpgrade}>
                      Upgrade
                    </Button>
                  ) : null}
                </div>
              )}
            </DisableIfNoAccess>
          }
        />

        <DataTable
          columns={columns}
          rows={rows}
          getRowId={(row) => row.id}
          loading={ordersQuery.isLoading}
          error={ordersQuery.error?.message}
          onRetry={() => void ordersQuery.refetch()}
          emptyTitle="No orders"
          emptyDescription="Create a new order to start the workflow."
          selection={{
            selectedIds,
            onToggle: onToggleRow,
            onToggleAll: onToggleAllRows
          }}
          bulkActions={[
            {
              id: "clear",
              label: "Clear selection",
              onClick: () => setSelectedIds(new Set())
            }
          ]}
          rowActions={[
            {
              id: "edit",
              label: "Edit",
              onClick: openEditModal,
              variant: "secondary",
              disabled: () => !canAccess("orders.edit")
            },
            {
              id: "start",
              label: "Start",
              onClick: (row) => statusMutation.mutate({ orderId: row.id, status: "in_progress" }),
              hidden: (row) => row.status !== "new",
              disabled: () => !canAccess("orders.change_status")
            },
            {
              id: "ready",
              label: "Ready",
              onClick: (row) => statusMutation.mutate({ orderId: row.id, status: "completed" }),
              hidden: (row) => row.status !== "in_progress",
              disabled: () => !canAccess("orders.change_status")
            },
            {
              id: "pay",
              label: "Pay",
              onClick: (row) => payMutation.mutate({ orderId: row.id }),
              hidden: (row) => row.status !== "completed",
              disabled: () => !canAccess("finance.create_payment", { limitType: "maxPaymentsPerMonth", increment: 1 })
            },
            {
              id: "cancel",
              label: "Cancel",
              onClick: (row) => setCancelOrderId(row.id),
              variant: "destructive",
              hidden: (row) => row.status === "canceled",
              disabled: () => !canAccess("orders.change_status")
            }
          ]}
          pagination={{
            page,
            pageSize: PAGE_SIZE,
            total: ordersQuery.data?.total ?? 0,
            onPageChange: setPage
          }}
        />
      </Section>

      <Modal
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        title="Create order"
        description="Fast operator flow with minimal fields"
        size="md"
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="create-order-form" variant="primary" loading={createMutation.isPending}>
              Create order
            </Button>
          </FormActions>
        }
      >
        <form id="create-order-form" className="space-y-3" onSubmit={(event) => void submitCreateOrder(event)}>
          <FormSection title="Order details" description="Only required fields for fast intake">
            <FormField id="create-phone" label="Phone" required error={createErrors.phone}>
              <Input
                id="create-phone"
                value={createForm.phone}
                onChange={(event) => setCreateForm((prev) => ({ ...prev, phone: event.target.value }))}
                invalid={Boolean(createErrors.phone)}
              />
            </FormField>

            <FormField id="create-client-name" label="Client name">
              <Input
                id="create-client-name"
                value={createForm.clientName}
                onChange={(event) => setCreateForm((prev) => ({ ...prev, clientName: event.target.value }))}
              />
            </FormField>

            <FormField id="create-price" label="Price" required error={createErrors.price}>
              <Input
                id="create-price"
                value={createForm.price}
                onChange={(event) => setCreateForm((prev) => ({ ...prev, price: event.target.value }))}
                invalid={Boolean(createErrors.price)}
              />
            </FormField>
          </FormSection>

          <FormField id="create-description" label="Work description" required error={createErrors.description}>
            <Textarea
              id="create-description"
              value={createForm.description}
              onChange={(event) => setCreateForm((prev) => ({ ...prev, description: event.target.value }))}
              invalid={Boolean(createErrors.description)}
            />
          </FormField>

          {createError ? <p className="text-sm text-error">{createError}</p> : null}
        </form>
      </Modal>

      <Modal
        open={editModalOpen}
        onOpenChange={(nextOpen) => {
          setEditModalOpen(nextOpen);
          if (!nextOpen) {
            setEditingOrder(null);
            setEditForm(defaultEditOrderForm());
          }
        }}
        title="Edit order"
        description={editingOrder ? `Order ${editingOrder.id.slice(0, 8)}` : undefined}
        size="md"
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setEditModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="edit-order-form" variant="primary" loading={updateMutation.isPending}>
              Save
            </Button>
          </FormActions>
        }
      >
        <form id="edit-order-form" className="space-y-3" onSubmit={(event) => void submitEditOrder(event)}>
          <FormSection title="Order update">
            <FormField id="edit-price" label="Price" required error={editErrors.price}>
              <Input
                id="edit-price"
                value={editForm.price}
                onChange={(event) => setEditForm((prev) => ({ ...prev, price: event.target.value }))}
                invalid={Boolean(editErrors.price)}
              />
            </FormField>

            <FormField id="edit-status" label="Status">
              <select
                id="edit-status"
                className="h-5 w-full rounded-sm border border-neutral-300 bg-neutral-0 px-2 text-sm text-neutral-900"
                value={editForm.status}
                onChange={(event) => setEditForm((prev) => ({ ...prev, status: event.target.value as OrderStatus }))}
              >
                <option value="new">New</option>
                <option value="in_progress">In progress</option>
                <option value="completed">Completed</option>
                <option value="canceled">Canceled</option>
              </select>
            </FormField>
          </FormSection>

          <FormField id="edit-description" label="Description" required error={editErrors.description}>
            <Textarea
              id="edit-description"
              value={editForm.description}
              onChange={(event) => setEditForm((prev) => ({ ...prev, description: event.target.value }))}
              invalid={Boolean(editErrors.description)}
            />
          </FormField>

          {editError ? <p className="text-sm text-error">{editError}</p> : null}
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(cancelOrderId)}
        onOpenChange={(open) => {
          if (!open) {
            setCancelOrderId(null);
          }
        }}
        title="Cancel order"
        description="Order will be moved to canceled status."
        confirmLabel="Cancel order"
        destructive
        loading={statusMutation.isPending}
        onConfirm={() => {
          if (!cancelOrderId) {
            return;
          }
          statusMutation.mutate(
            { orderId: cancelOrderId, status: "canceled" },
            {
              onSuccess: () => {
                setCancelOrderId(null);
              }
            }
          );
        }}
      />
    </PageLayout>
  );
}


