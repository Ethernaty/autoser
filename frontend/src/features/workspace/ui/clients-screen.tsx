"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { formatPhoneForDisplay, formatPhoneInput, normalizePhoneForSubmit } from "@/core/lib/phone";
import { ROUTES } from "@/core/config/routes";
import { DataTable } from "@/design-system/primitives/data-table/data-table";
import type { DataTableColumn } from "@/design-system/primitives/data-table/data-table.types";
import { Button, FormActions, FormField, Input, Modal, PhoneInput, Textarea } from "@/design-system/primitives";
import { PageLayout, Section, Toolbar } from "@/design-system/patterns";
import { createClient, fetchClients, mvpQueryKeys, updateClient } from "@/features/workspace/api/mvp-api";
import type { ClientRecord } from "@/features/workspace/types/mvp-types";

const PAGE_SIZE = 20;

type ClientForm = {
  name: string;
  phone: string;
  email: string;
  comment: string;
};

function defaultClientForm(): ClientForm {
  return {
    name: "",
    phone: "",
    email: "",
    comment: ""
  };
}

export function ClientsScreen(): JSX.Element {
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const initialQ = searchParams.get("q") ?? "";
  const initialPageRaw = Number(searchParams.get("page") ?? "1");
  const initialPage = Number.isFinite(initialPageRaw) && initialPageRaw > 0 ? initialPageRaw : 1;

  const [q, setQ] = useState(initialQ);
  const [search, setSearch] = useState(initialQ);
  const [page, setPage] = useState(initialPage);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<ClientRecord | null>(null);
  const [form, setForm] = useState<ClientForm>(defaultClientForm());
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    const nextQ = searchParams.get("q") ?? "";
    const nextPageRaw = Number(searchParams.get("page") ?? "1");
    const nextPage = Number.isFinite(nextPageRaw) && nextPageRaw > 0 ? nextPageRaw : 1;
    setQ(nextQ);
    setSearch(nextQ);
    setPage(nextPage);
  }, [searchParams]);

  const offset = (page - 1) * PAGE_SIZE;

  const updateUrlState = (next: { q: string; page: number }): void => {
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
    const queryString = params.toString();
    const nextHref = queryString ? `${pathname}?${queryString}` : pathname;
    router.replace(nextHref as Route, { scroll: false });
  };

  const clientsQuery = useQuery({
    queryKey: mvpQueryKeys.clients(q, PAGE_SIZE, offset),
    queryFn: () => fetchClients({ q, limit: PAGE_SIZE, offset }),
    placeholderData: keepPreviousData
  });

  const createMutation = useMutation({
    mutationFn: createClient,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["clients"] });
    }
  });

  const updateMutation = useMutation({
    mutationFn: ({ clientId, payload }: { clientId: string; payload: Parameters<typeof updateClient>[1] }) =>
      updateClient(clientId, payload),
    onSuccess: (_, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["clients"] });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.client(variables.clientId) });
    }
  });

  const onOpenCreate = (): void => {
    setEditingClient(null);
    setForm(defaultClientForm());
    setFormError(null);
    setModalOpen(true);
  };

  const onOpenEdit = (client: ClientRecord): void => {
    setEditingClient(client);
    setForm({
      name: client.name,
      phone: formatPhoneInput(client.phone),
      email: client.email ?? "",
      comment: client.comment ?? ""
    });
    setFormError(null);
    setModalOpen(true);
  };

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();

    if (!form.name.trim() || !form.phone.trim()) {
      setFormError("Name and phone are required.");
      return;
    }
    setFormError(null);

    if (editingClient) {
      await updateMutation.mutateAsync({
        clientId: editingClient.id,
        payload: {
          name: form.name.trim(),
          phone: normalizePhoneForSubmit(form.phone),
          email: form.email.trim() ? form.email.trim() : null,
          comment: form.comment.trim() ? form.comment.trim() : null,
          version: editingClient.version
        }
      });
    } else {
      await createMutation.mutateAsync({
        name: form.name.trim(),
        phone: normalizePhoneForSubmit(form.phone),
        email: form.email.trim() ? form.email.trim() : null,
        comment: form.comment.trim() ? form.comment.trim() : null
      });
    }

    setModalOpen(false);
    setEditingClient(null);
    setForm(defaultClientForm());
  };

  const rows = clientsQuery.data?.items ?? [];

  const columns = useMemo<DataTableColumn<ClientRecord>[]>(
    () => [
      {
        id: "name",
        header: "Name",
        minWidth: 220,
        cell: (row) => (
          <Link href={ROUTES.clientDetail(row.id) as Route} className="font-medium text-primary hover:underline">
            {row.name}
          </Link>
        )
      },
      {
        id: "phone",
        header: "Phone",
        minWidth: 180,
        cell: (row) => formatPhoneForDisplay(row.phone)
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
        align: "right",
        cell: (row) => new Date(row.updated_at).toLocaleString()
      }
    ],
    []
  );

  return (
    <PageLayout title="Clients" subtitle="Client records for daily operations">
      <Section>
        <Toolbar
          leading={
            <form
              className="flex items-center gap-1"
              onSubmit={(event) => {
                event.preventDefault();
                const nextQ = search.trim();
                setQ(nextQ);
                setPage(1);
                updateUrlState({ q: nextQ, page: 1 });
              }}
            >
              <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search clients" />
              <Button type="submit" variant="secondary">
                Search
              </Button>
            </form>
          }
          trailing={
            <Button onClick={onOpenCreate} variant="primary">
              Add client
            </Button>
          }
        />
      </Section>

      <Section>
        <DataTable
          columns={columns}
          rows={rows}
          getRowId={(row) => row.id}
          loading={clientsQuery.isLoading}
          error={clientsQuery.error?.message}
          onRetry={() => void clientsQuery.refetch()}
          emptyTitle="No clients"
          emptyDescription="Create your first client to start."
          rowActions={[
            {
              id: "open",
              label: "Details",
              onClick: (row) => {
                router.push(ROUTES.clientDetail(row.id) as Route);
              }
            },
            {
              id: "edit",
              label: "Edit",
              onClick: onOpenEdit,
              variant: "secondary"
            }
          ]}
          pagination={{
            page,
            pageSize: PAGE_SIZE,
            total: clientsQuery.data?.total ?? 0,
            onPageChange: (nextPage) => {
              setPage(nextPage);
              updateUrlState({ q, page: nextPage });
            }
          }}
        />
      </Section>

      <Modal
        open={modalOpen}
        onOpenChange={setModalOpen}
        title={editingClient ? "Edit client" : "Create client"}
        description={editingClient ? "Update client details" : "Create a new client card"}
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="client-form" loading={createMutation.isPending || updateMutation.isPending}>
              {editingClient ? "Save" : "Create"}
            </Button>
          </FormActions>
        }
      >
        <form id="client-form" className="space-y-2" onSubmit={(event) => void onSubmit(event)}>
          <FormField id="client-name" label="Name" required>
            <Input id="client-name" value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} />
          </FormField>
          <FormField id="client-phone" label="Phone" required>
            <PhoneInput id="client-phone" value={form.phone} onChange={(phone) => setForm((prev) => ({ ...prev, phone }))} />
          </FormField>
          <FormField id="client-email" label="Email">
            <Input id="client-email" value={form.email} onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))} />
          </FormField>
          <FormField id="client-comment" label="Comment">
            <Textarea
              id="client-comment"
              value={form.comment}
              onChange={(event) => setForm((prev) => ({ ...prev, comment: event.target.value }))}
            />
          </FormField>
          {formError ? <p className="text-sm text-error">{formError}</p> : null}
          {createMutation.error ? <p className="text-sm text-error">{createMutation.error.message}</p> : null}
          {updateMutation.error ? <p className="text-sm text-error">{updateMutation.error.message}</p> : null}
        </form>
      </Modal>
    </PageLayout>
  );
}
