"use client";

import { Search, UserPlus } from "lucide-react";
import { useMemo, useState } from "react";

import { DataTable } from "@/design-system/primitives/data-table/data-table";
import type { DataTableColumn } from "@/design-system/primitives/data-table/data-table.types";
import { Button } from "@/design-system/primitives/button";
import { FormActions } from "@/design-system/primitives/form-actions";
import { FormField } from "@/design-system/primitives/form-field";
import { FormSection } from "@/design-system/primitives/form-section";
import { Input } from "@/design-system/primitives/input";
import { Modal } from "@/design-system/primitives/modal";
import { Textarea } from "@/design-system/primitives/textarea";
import { PageLayout, Section, Toolbar } from "@/design-system/patterns";
import { useAccess } from "@/features/access/hooks/use-access";
import { DisableIfNoAccess } from "@/features/access/ui/access-guard";
import {
  useCreateClientMutation,
  useUpdateClientMutation,
  useWorkspaceClientsQuery
} from "@/features/workspace/hooks";
import type { ClientRecord } from "@/features/workspace/types";

const PAGE_SIZE = 20;

type ClientFormState = {
  name: string;
  phone: string;
  email: string;
  comment: string;
};

function defaultFormState(): ClientFormState {
  return {
    name: "",
    phone: "",
    email: "",
    comment: ""
  };
}

function validateForm(state: ClientFormState): Record<string, string> {
  const errors: Record<string, string> = {};

  if (!state.name.trim()) {
    errors.name = "Name is required";
  }

  if (!state.phone.trim()) {
    errors.phone = "Phone is required";
  }

  if (state.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(state.email.trim())) {
    errors.email = "Invalid email format";
  }

  return errors;
}

export function ClientsScreen(): JSX.Element {
  const { canAccess } = useAccess();

  const [searchInput, setSearchInput] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const [modalOpen, setModalOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<ClientRecord | null>(null);
  const [formState, setFormState] = useState<ClientFormState>(defaultFormState());
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  const offset = (page - 1) * PAGE_SIZE;
  const clientsQuery = useWorkspaceClientsQuery({ q: query, limit: PAGE_SIZE, offset });

  const createMutation = useCreateClientMutation();
  const updateMutation = useUpdateClientMutation();

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const mutationError = createMutation.error?.message ?? updateMutation.error?.message ?? null;

  const rows = clientsQuery.data?.items ?? [];

  const columns = useMemo<DataTableColumn<ClientRecord>[]>(
    () => [
      {
        id: "name",
        header: "Name",
        minWidth: 220,
        cell: (row) => <span className="font-medium text-neutral-900">{row.name}</span>
      },
      {
        id: "phone",
        header: "Phone",
        minWidth: 180,
        cell: (row) => row.phone
      },
      {
        id: "email",
        header: "Email",
        minWidth: 220,
        cell: (row) => row.email ?? "-"
      },
      {
        id: "updated",
        header: "Updated",
        minWidth: 180,
        cell: (row) => new Date(row.updated_at).toLocaleString(),
        align: "right"
      }
    ],
    []
  );

  const resetModalState = (): void => {
    setFormState(defaultFormState());
    setFormErrors({});
    setEditingClient(null);
  };

  const openCreateModal = (): void => {
    resetModalState();
    setModalOpen(true);
  };

  const openEditModal = (client: ClientRecord): void => {
    setEditingClient(client);
    setFormState({
      name: client.name,
      phone: client.phone,
      email: client.email ?? "",
      comment: client.comment ?? ""
    });
    setFormErrors({});
    setModalOpen(true);
  };

  const closeModal = (): void => {
    setModalOpen(false);
    resetModalState();
  };

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

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();

    const errors = validateForm(formState);
    setFormErrors(errors);

    if (Object.keys(errors).length > 0) {
      return;
    }

    if (editingClient) {
      await updateMutation.mutateAsync({
        clientId: editingClient.id,
        name: formState.name.trim(),
        phone: formState.phone.trim(),
        email: formState.email.trim() ? formState.email.trim() : null,
        comment: formState.comment.trim() ? formState.comment.trim() : null,      });
    } else {
      await createMutation.mutateAsync({
        name: formState.name.trim(),
        phone: formState.phone.trim(),
        email: formState.email.trim() ? formState.email.trim() : null,
        comment: formState.comment.trim() ? formState.comment.trim() : null
      });
    }

    closeModal();
  };

  return (
    <PageLayout title="Clients" subtitle="Customer base for operators and managers">
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
                  placeholder="Search by name, phone or email"
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
            <DisableIfNoAccess permission="clients.create">
              {(disabled) => (
                <Button variant="primary" disabled={disabled} onClick={openCreateModal}>
                  <UserPlus className="h-2.5 w-2.5" />
                  Add client
                </Button>
              )}
            </DisableIfNoAccess>
          }
        />

        <DataTable
          columns={columns}
          rows={rows}
          getRowId={(row) => row.id}
          loading={clientsQuery.isLoading}
          error={clientsQuery.error?.message}
          onRetry={() => void clientsQuery.refetch()}
          emptyTitle="No clients"
          emptyDescription="Create your first client to start taking orders faster."
          selection={{
            selectedIds,
            onToggle: onToggleRow,
            onToggleAll: onToggleAllRows
          }}
          bulkActions={[
            {
              id: "clear",
              label: "Clear selection",
              onClick: () => setSelectedIds(new Set()),
              variant: "secondary"
            }
          ]}
          rowActions={[
            {
              id: "edit",
              label: "Edit",
              onClick: openEditModal,
              variant: "secondary",
              disabled: () => !canAccess("clients.edit")
            }
          ]}
          pagination={{
            page,
            pageSize: PAGE_SIZE,
            total: clientsQuery.data?.total ?? 0,
            onPageChange: setPage
          }}
        />
      </Section>

      <Modal
        open={modalOpen}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) {
            closeModal();
            return;
          }
          setModalOpen(true);
        }}
        title={editingClient ? "Edit client" : "Add client"}
        description={editingClient ? "Update client contact details" : "Create a new client card"}
        size="md"
        footer={
          <FormActions>
            <Button variant="secondary" type="button" onClick={closeModal}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" form="client-form" loading={isSaving}>
              {editingClient ? "Save changes" : "Create client"}
            </Button>
          </FormActions>
        }
      >
        <form id="client-form" className="space-y-3" onSubmit={(event) => void onSubmit(event)}>
          <FormSection title="Client info" description="Required fields are marked with *">
            <FormField id="client-name" label="Name" required error={formErrors.name}>
              <Input
                id="client-name"
                value={formState.name}
                onChange={(event) => setFormState((prev) => ({ ...prev, name: event.target.value }))}
                invalid={Boolean(formErrors.name)}
              />
            </FormField>

            <FormField id="client-phone" label="Phone" required error={formErrors.phone}>
              <Input
                id="client-phone"
                value={formState.phone}
                onChange={(event) => setFormState((prev) => ({ ...prev, phone: event.target.value }))}
                invalid={Boolean(formErrors.phone)}
              />
            </FormField>

            <FormField id="client-email" label="Email" error={formErrors.email}>
              <Input
                id="client-email"
                value={formState.email}
                onChange={(event) => setFormState((prev) => ({ ...prev, email: event.target.value }))}
                invalid={Boolean(formErrors.email)}
              />
            </FormField>

            <FormField id="client-comment" label="Comment">
              <Textarea
                id="client-comment"
                value={formState.comment}
                onChange={(event) => setFormState((prev) => ({ ...prev, comment: event.target.value }))}
              />
            </FormField>
          </FormSection>

          {mutationError ? <p className="text-sm text-error">{mutationError}</p> : null}
        </form>
      </Modal>
    </PageLayout>
  );
}







