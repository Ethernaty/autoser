"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { formatPhoneForDisplay, formatPhoneInput, normalizePhoneForSubmit } from "@/core/lib/phone";
import { ROUTES } from "@/core/config/routes";
import { Badge, Button, FormActions, FormField, Input, MobilePagination, Modal, PhoneInput, Select, Textarea } from "@/design-system/primitives";
import { PageLayout } from "@/design-system/patterns";
import { createClient, fetchClients, mvpQueryKeys, updateClient } from "@/features/workspace/api/mvp-api";
import type { ClientRecord } from "@/features/workspace/types/mvp-types";
import { useI18n } from "@/shared/i18n";

const PAGE_SIZE = 20;

type ClientForm = {
  name: string;
  phone: string;
  email: string;
  source: string;
  comment: string;
};

function defaultClientForm(): ClientForm {
  return {
    name: "",
    phone: "",
    email: "",
    source: "",
    comment: ""
  };
}

type ClientSortMode = "recent" | "name" | "activity";

function toTimestamp(value: string | null | undefined): number {
  if (!value) return 0;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString();
}

function RegistryStat({
  label,
  value
}: {
  label: string;
  value: string | number;
}): JSX.Element {
  return (
    <div className="min-w-0 rounded-md border border-neutral-200 bg-neutral-0 px-3 py-2">
      <p className="truncate text-[10px] font-semibold uppercase tracking-wide text-neutral-500">{label}</p>
      <p className="mt-1 text-lg font-semibold leading-none tabular-nums text-neutral-900">{value}</p>
    </div>
  );
}

export function ClientsScreen(): JSX.Element {
  const { t } = useI18n();
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
  const [sortMode, setSortMode] = useState<ClientSortMode>("recent");
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

  const updateUrlState = useCallback(
    (next: { q: string; page: number }): void => {
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
      updateUrlState({ q: nextQ, page: 1 });
    }, 250);

    return () => {
      window.clearTimeout(timeout);
    };
  }, [q, search, updateUrlState]);

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
      source: client.source ?? "",
      comment: client.comment ?? ""
    });
    setFormError(null);
    setModalOpen(true);
  };

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();

    if (!form.name.trim() || !form.phone.trim()) {
      setFormError(t("clients.form.error.required"));
      return;
    }

    const normalizedPhone = normalizePhoneForSubmit(form.phone);
    if (!normalizedPhone) {
      setFormError(t("clients.form.error.phone"));
      return;
    }

    try {
      const lookup = await fetchClients({ q: normalizedPhone, limit: 20, offset: 0 });
      const duplicate = lookup.items.find((item) => item.phone === normalizedPhone);
      if (duplicate && (!editingClient || duplicate.id !== editingClient.id)) {
        setFormError(t("clients.form.error.duplicate", { name: duplicate.name }));
        return;
      }
    } catch {
      // backend remains source of truth
    }

    setFormError(null);

    if (editingClient) {
      await updateMutation.mutateAsync({
        clientId: editingClient.id,
        payload: {
          name: form.name.trim(),
          phone: normalizedPhone,
          email: form.email.trim() ? form.email.trim() : null,
          source: form.source.trim() ? form.source.trim() : null,
          comment: form.comment.trim() ? form.comment.trim() : null,
          version: editingClient.version
        }
      });
    } else {
      await createMutation.mutateAsync({
        name: form.name.trim(),
        phone: normalizedPhone,
        email: form.email.trim() ? form.email.trim() : null,
        source: form.source.trim() ? form.source.trim() : null,
        comment: form.comment.trim() ? form.comment.trim() : null
      });
    }

    setModalOpen(false);
    setEditingClient(null);
    setForm(defaultClientForm());
  };

  const totalClients = clientsQuery.data?.total ?? 0;
  const visibleRows = useMemo(() => {
    const nextRows = [...(clientsQuery.data?.items ?? [])];
    nextRows.sort((a, b) => {
      if (sortMode === "name") {
        return a.name.localeCompare(b.name, "ru");
      }
      if (sortMode === "activity") {
        const aTotal = a.work_order_count ?? 0;
        const bTotal = b.work_order_count ?? 0;
        if (bTotal !== aTotal) {
          return bTotal - aTotal;
        }
        return toTimestamp(b.last_activity_at) - toTimestamp(a.last_activity_at);
      }
      return toTimestamp(b.updated_at) - toTimestamp(a.updated_at);
    });
    return nextRows;
  }, [clientsQuery.data?.items, sortMode]);

  const summary = useMemo(() => {
    let activeClients = 0;
    let withVehicles = 0;
    let withoutOrders = 0;

    for (const client of visibleRows) {
      if ((client.work_order_count ?? 0) > 0) {
        activeClients += 1;
      } else {
        withoutOrders += 1;
      }
      if ((client.vehicle_count ?? 0) > 0) {
        withVehicles += 1;
      }
    }

    return {
      activeClients,
      withVehicles,
      withoutOrders
    };
  }, [visibleRows]);

  const hasAnyFilterActive = Boolean(search.trim()) || sortMode !== "recent";

  const clearFilters = (): void => {
    setSearch("");
    setQ("");
    setPage(1);
    setSortMode("recent");
    updateUrlState({ q: "", page: 1 });
  };

  return (
    <PageLayout
      title={t("clients.title")}
      subtitle={t("clients.subtitle")}
      className="space-y-2"
      actions={
        <Button onClick={onOpenCreate} variant="primary">
          {t("clients.add")}
        </Button>
      }
    >
      <div className="space-y-2">
        <div className="flex flex-col gap-2 rounded-md border border-neutral-200 bg-neutral-0 p-2 md:flex-row md:items-center">
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("clients.search_placeholder")}
            className="min-w-0 md:flex-1"
          />
          <div className="flex items-center gap-2 md:w-auto">
            <Select
              size="sm"
              variant="subtle"
              value={sortMode}
              triggerLabel={t("clients.sort.label")}
              className="h-8 min-w-[180px]"
              onChange={(event) => setSortMode(event.target.value as ClientSortMode)}
            >
              <option value="recent">{t("clients.sort.recent")}</option>
              <option value="name">{t("clients.sort.name")}</option>
              <option value="activity">{t("clients.sort.activity")}</option>
            </Select>
            {hasAnyFilterActive ? (
              <Button size="sm" variant="ghost" className="h-8 px-2 text-neutral-500 hover:text-neutral-700" onClick={clearFilters}>
                {t("work_orders.toolbar.clear_filters")}
              </Button>
            ) : null}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          <RegistryStat label={t("clients.kpi.total")} value={totalClients} />
          <RegistryStat label={t("clients.kpi.active")} value={summary.activeClients} />
          <RegistryStat label={t("clients.kpi.with_vehicles")} value={summary.withVehicles} />
          <RegistryStat label={t("clients.kpi.without_orders")} value={summary.withoutOrders} />
        </div>

        <div className="space-y-1.5 md:hidden">
          {clientsQuery.isLoading ? (
            Array.from({ length: 4 }).map((_, index) => (
              <div key={`client-skeleton-${index}`} className="h-[112px] rounded-md border border-neutral-200 bg-neutral-0 p-2.5">
                <div className="h-3 w-2/3 rounded bg-neutral-100" />
                <div className="mt-2 h-2.5 w-4/5 rounded bg-neutral-100" />
                <div className="mt-2 h-2.5 w-1/2 rounded bg-neutral-100" />
              </div>
            ))
          ) : clientsQuery.error ? (
            <div className="rounded-md border border-error/30 bg-error/5 p-2.5">
              <p className="text-sm text-error">{clientsQuery.error.message}</p>
              <Button className="mt-2" size="sm" variant="secondary" onClick={() => void clientsQuery.refetch()}>
                {t("datatable.retry")}
              </Button>
            </div>
          ) : visibleRows.length ? (
            visibleRows.map((client) => {
              return (
                <article
                  key={client.id}
                  className="w-full rounded-md border border-neutral-200 bg-neutral-0 p-2.5 transition-colors hover:border-neutral-300 hover:bg-neutral-50"
                >
                  <button
                    type="button"
                    onClick={() => router.push(ROUTES.clientDetail(client.id) as Route)}
                    className="w-full text-left"
                  >
                    <p className="truncate text-sm font-semibold text-neutral-900">{client.name}</p>
                    <p className="mt-1 truncate text-xs text-neutral-600">
                      {formatPhoneForDisplay(client.phone)}
                      {client.email ? ` | ${client.email}` : ""}
                      {client.source ? ` | ${client.source}` : ""}
                    </p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                      <Badge tone="neutral">{t("clients.table.vehicles_count_short", { count: client.vehicle_count ?? 0 })}</Badge>
                      <Badge tone={(client.active_work_order_count ?? 0) > 0 ? "warning" : "neutral"}>
                        {t("clients.table.orders_count_short", { count: client.work_order_count ?? 0 })}
                      </Badge>
                    </div>
                    <p className="mt-1 truncate text-[11px] text-neutral-500">
                      {client.last_activity_at
                        ? t("clients.table.last_activity", { date: formatDateTime(client.last_activity_at) })
                        : t("clients.table.no_activity")}
                    </p>
                  </button>
                  <div className="mt-2 flex items-center justify-end gap-1.5 border-t border-neutral-200 pt-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="primary"
                      className="h-8"
                      onClick={() => router.push(ROUTES.clientDetail(client.id) as Route)}
                    >
                      {t("common.open")}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      className="h-8"
                      onClick={() => onOpenEdit(client)}
                    >
                      {t("common.edit")}
                    </Button>
                  </div>
                </article>
              );
            })
          ) : (
            <div className="rounded-md border border-neutral-200 bg-neutral-0 p-3 text-center">
              <p className="text-sm font-semibold text-neutral-900">{t("clients.empty.title")}</p>
              <p className="mt-1 text-xs text-neutral-600">{t("clients.empty.description")}</p>
              <Button className="mt-2" variant="primary" onClick={onOpenCreate}>
                {t("clients.add")}
              </Button>
            </div>
          )}
          <MobilePagination
            page={page}
            pageSize={PAGE_SIZE}
            total={totalClients}
            onPageChange={(nextPage) => {
              setPage(nextPage);
              updateUrlState({ q, page: nextPage });
            }}
            label="{page}/{total}"
            prevLabel={t("datatable.pagination.prev")}
            nextLabel={t("datatable.pagination.next")}
          />
        </div>

        <div className="hidden md:block">
          <div className="overflow-hidden rounded-md border border-neutral-200 bg-neutral-0 shadow-sm">
            <div className="grid grid-cols-[minmax(0,2fr)_minmax(0,1.8fr)_minmax(0,1.1fr)_minmax(0,1.4fr)_minmax(0,1.1fr)_auto] gap-2 border-b border-neutral-200 bg-neutral-50 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-neutral-600">
              <div>{t("clients.table.client")}</div>
              <div>{t("clients.table.contacts")}</div>
              <div>{t("clients.table.vehicles")}</div>
              <div>{t("clients.table.activity")}</div>
              <div>{t("clients.table.last_update")}</div>
              <div className="text-right">{t("common.actions")}</div>
            </div>

            {clientsQuery.isLoading ? (
              <div className="space-y-2 p-3">
                {Array.from({ length: 5 }).map((_, index) => (
                  <div key={`clients-row-skeleton-${index}`} className="h-10 rounded-md bg-neutral-100" />
                ))}
              </div>
            ) : clientsQuery.error ? (
              <div className="p-3">
                <div className="rounded-md border border-error/30 bg-error/5 p-3">
                  <p className="text-sm text-error">{clientsQuery.error.message}</p>
                  <Button className="mt-2" size="sm" variant="secondary" onClick={() => void clientsQuery.refetch()}>
                    {t("datatable.retry")}
                  </Button>
                </div>
              </div>
            ) : visibleRows.length ? (
              <div>
                {visibleRows.map((client) => {
                  return (
                    <div
                      key={client.id}
                      className="grid grid-cols-[minmax(0,2fr)_minmax(0,1.8fr)_minmax(0,1.1fr)_minmax(0,1.4fr)_minmax(0,1.1fr)_auto] gap-2 border-b border-neutral-200 px-3 py-2.5 text-sm last:border-b-0 hover:bg-neutral-50"
                    >
                      <button type="button" className="min-w-0 text-left" onClick={() => router.push(ROUTES.clientDetail(client.id) as Route)}>
                        <p className="truncate font-semibold text-primary">{client.name}</p>
                        {client.source ? <p className="truncate text-xs text-neutral-600">{client.source}</p> : null}
                      </button>

                      <div className="min-w-0">
                        <p className="truncate text-sm text-neutral-900">{formatPhoneForDisplay(client.phone)}</p>
                        {client.email ? <p className="truncate text-xs text-neutral-600">{client.email}</p> : null}
                      </div>

                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-neutral-900">{client.vehicle_count ?? 0}</p>
                        <p className="truncate text-xs text-neutral-600">{t("clients.table.vehicles")}</p>
                      </div>

                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-neutral-900">{t("clients.table.orders_count", { count: client.work_order_count ?? 0 })}</p>
                        <p className="truncate text-xs text-neutral-600">
                          {client.last_activity_at
                            ? t("clients.table.last_activity", { date: formatDateTime(client.last_activity_at) })
                            : t("clients.table.no_activity")}
                        </p>
                        {(client.active_work_order_count ?? 0) > 0 ? (
                          <p className="text-xs font-medium text-warning">
                            {t("clients.table.active_orders", { count: client.active_work_order_count ?? 0 })}
                          </p>
                        ) : null}
                      </div>

                      <div className="text-xs text-neutral-600">{formatDateTime(client.updated_at)}</div>

                      <div className="flex items-center justify-end gap-1.5">
                        <Button size="sm" variant="secondary" onClick={() => router.push(ROUTES.clientDetail(client.id) as Route)}>{t("common.open")}</Button>
                        <Button size="sm" variant="ghost" onClick={() => onOpenEdit(client)}>{t("common.edit")}</Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-3">
                <div className="rounded-md border border-neutral-200 bg-neutral-50 px-4 py-6 text-center">
                  <p className="text-sm font-semibold text-neutral-900">{t("clients.empty.title")}</p>
                  <p className="mt-1 text-sm text-neutral-600">{t("clients.empty.description")}</p>
                  <Button className="mt-3" variant="primary" onClick={onOpenCreate}>
                    {t("clients.add")}
                  </Button>
                </div>
              </div>
            )}

            {totalClients > 0 ? (
              <div className="border-t border-neutral-200 bg-neutral-50 px-3 py-2">
                <MobilePagination
                  page={page}
                  pageSize={PAGE_SIZE}
                  total={totalClients}
                  onPageChange={(nextPage) => {
                    setPage(nextPage);
                    updateUrlState({ q, page: nextPage });
                  }}
                  label="{page}/{total}"
                  prevLabel={t("datatable.pagination.prev")}
                  nextLabel={t("datatable.pagination.next")}
                />
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <Modal
        open={modalOpen}
        onOpenChange={setModalOpen}
        title={editingClient ? t("clients.modal.edit_title") : t("clients.modal.create_title")}
        description={editingClient ? t("clients.modal.edit_description") : t("clients.modal.create_description")}
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" form="client-form" loading={createMutation.isPending || updateMutation.isPending}>
              {editingClient ? t("common.save") : t("common.create")}
            </Button>
          </FormActions>
        }
      >
        <form id="client-form" className="space-y-2" onSubmit={(event) => void onSubmit(event)}>
          <FormField id="client-name" label={t("clients.form.full_name")} required>
            <Input id="client-name" value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} />
          </FormField>
          <FormField id="client-phone" label={t("common.phone")} required>
            <PhoneInput id="client-phone" value={form.phone} onChange={(phone) => setForm((prev) => ({ ...prev, phone }))} />
          </FormField>
          <FormField id="client-email" label={t("common.email")}>
            <Input id="client-email" value={form.email} onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))} />
          </FormField>
          <FormField id="client-source" label={t("clients.form.source")}>
            <Input
              id="client-source"
              value={form.source}
              onChange={(event) => setForm((prev) => ({ ...prev, source: event.target.value }))}
              placeholder={t("clients.form.source_placeholder")}
            />
          </FormField>
          <FormField id="client-comment" label={t("common.comment")}>
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
