"use client";

import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import { formatPhoneForDisplay } from "@/core/lib/phone";
import { normalizePlateForSubmit, normalizeVinForSubmit } from "@/core/lib/vehicle";
import { Badge, Button, Combobox, FormActions, FormField, Input, MobilePagination, Modal, Select, Textarea } from "@/design-system/primitives";
import { PageLayout } from "@/design-system/patterns";
import {
  createVehicle,
  fetchClients,
  fetchVehicles,
  mvpQueryKeys,
  updateVehicle
} from "@/features/workspace/api/mvp-api";
import type { VehicleRecord } from "@/features/workspace/types/mvp-types";
import { useI18n } from "@/shared/i18n";

const PAGE_SIZE = 20;

type VehicleForm = {
  client_id: string;
  plate_number: string;
  make_model: string;
  year: string;
  vin: string;
  comment: string;
};

function defaultVehicleForm(): VehicleForm {
  return {
    client_id: "",
    plate_number: "",
    make_model: "",
    year: "",
    vin: "",
    comment: ""
  };
}

type VehicleSortMode = "recent" | "plate" | "owner" | "history";

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

export function VehiclesScreen(): JSX.Element {
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
  const [sortMode, setSortMode] = useState<VehicleSortMode>("recent");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState<VehicleRecord | null>(null);
  const [form, setForm] = useState<VehicleForm>(defaultVehicleForm());
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    const nextQ = searchParams.get("q") ?? "";
    const nextPageRaw = Number(searchParams.get("page") ?? "1");
    const nextPage = Number.isFinite(nextPageRaw) && nextPageRaw > 0 ? nextPageRaw : 1;
    setQ(nextQ);
    setSearch(nextQ);
    setPage(nextPage);
  }, [searchParams]);

  useEffect(() => {
    if (searchParams.get("create") !== "1") {
      return;
    }
    const presetClientId = searchParams.get("client_id") ?? "";
    setEditingVehicle(null);
    setForm({ ...defaultVehicleForm(), client_id: presetClientId });
    setFormError(null);
    setModalOpen(true);

    const params = new URLSearchParams(searchParams.toString());
    params.delete("create");
    params.delete("client_id");
    const queryString = params.toString();
    router.replace((queryString ? `${pathname}?${queryString}` : pathname) as Route, { scroll: false });
  }, [pathname, router, searchParams]);

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

  const vehiclesQuery = useQuery({
    queryKey: mvpQueryKeys.vehicles(q, "", PAGE_SIZE, offset),
    queryFn: () => fetchVehicles({ q, limit: PAGE_SIZE, offset }),
    placeholderData: keepPreviousData
  });
  const clientsQuery = useQuery({
    queryKey: mvpQueryKeys.clients("", 50, 0),
    queryFn: () => fetchClients({ limit: 50, offset: 0 }),
    refetchOnMount: true
  });

  const createMutation = useMutation({
    mutationFn: createVehicle,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["vehicles"] });
      void queryClient.invalidateQueries({ queryKey: ["clients"] });
    }
  });

  const updateMutation = useMutation({
    mutationFn: ({ vehicleId, payload }: { vehicleId: string; payload: Parameters<typeof updateVehicle>[1] }) =>
      updateVehicle(vehicleId, payload),
    onSuccess: (_, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["vehicles"] });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.vehicle(variables.vehicleId) });
    }
  });

  const totalVehicles = vehiclesQuery.data?.total ?? 0;
  const visibleRows = useMemo(() => {
    const nextRows = [...(vehiclesQuery.data?.items ?? [])];
    nextRows.sort((a, b) => {
      if (sortMode === "plate") {
        return a.plate_number.localeCompare(b.plate_number, "ru");
      }
      if (sortMode === "owner") {
        const aOwner = a.client_name ?? "";
        const bOwner = b.client_name ?? "";
        return aOwner.localeCompare(bOwner, "ru");
      }
      if (sortMode === "history") {
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
  }, [vehiclesQuery.data?.items, sortMode]);

  const summary = useMemo(() => {
    let withActiveOrders = 0;
    let withoutOrders = 0;
    let recentAdded = 0;
    const now = Date.now();
    const recentThreshold = 1000 * 60 * 60 * 24 * 14;

    for (const vehicle of visibleRows) {
      if ((vehicle.active_work_order_count ?? 0) > 0) {
        withActiveOrders += 1;
      }
      if ((vehicle.work_order_count ?? 0) === 0) {
        withoutOrders += 1;
      }
      if (now - toTimestamp(vehicle.created_at) <= recentThreshold) {
        recentAdded += 1;
      }
    }

    return { withActiveOrders, withoutOrders, recentAdded };
  }, [visibleRows]);

  const hasAnyFilterActive = Boolean(search.trim()) || sortMode !== "recent";
  const clearFilters = (): void => {
    setSearch("");
    setQ("");
    setPage(1);
    setSortMode("recent");
    updateUrlState({ q: "", page: 1 });
  };

  const onOpenCreate = (): void => {
    void clientsQuery.refetch();
    setEditingVehicle(null);
    setForm(defaultVehicleForm());
    setFormError(null);
    setModalOpen(true);
  };

  const onOpenEdit = (vehicle: VehicleRecord): void => {
    setEditingVehicle(vehicle);
    setForm({
      client_id: vehicle.client_id,
      plate_number: vehicle.plate_number,
      make_model: vehicle.make_model,
      year: vehicle.year ? String(vehicle.year) : "",
      vin: vehicle.vin ?? "",
      comment: vehicle.comment ?? ""
    });
    setFormError(null);
    setModalOpen(true);
  };

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    const normalizedPlate = normalizePlateForSubmit(form.plate_number);
    const normalizedVin = normalizeVinForSubmit(form.vin);

    if (!normalizedPlate || !form.make_model.trim()) {
      setFormError(t("vehicles.form.error.required"));
      return;
    }
    if (!editingVehicle && !form.client_id) {
      setFormError(t("vehicles.form.error.client_required"));
      return;
    }

    try {
      const plateLookup = await fetchVehicles({ q: normalizedPlate, limit: 50, offset: 0 });
      const duplicatePlate = plateLookup.items.find(
        (item) => normalizePlateForSubmit(item.plate_number) === normalizedPlate && (!editingVehicle || item.id !== editingVehicle.id)
      );
      if (duplicatePlate) {
        setFormError(t("vehicles.form.error.duplicate_plate", { plate: duplicatePlate.plate_number }));
        return;
      }

      if (normalizedVin) {
        const vinLookup = await fetchVehicles({ q: normalizedVin, limit: 50, offset: 0 });
        const duplicateVin = vinLookup.items.find(
          (item) => normalizeVinForSubmit(item.vin) === normalizedVin && (!editingVehicle || item.id !== editingVehicle.id)
        );
        if (duplicateVin) {
          setFormError(t("vehicles.form.error.duplicate_vin", { plate: duplicateVin.plate_number }));
          return;
        }
      }
    } catch {
      // backend remains source of truth
    }

    setFormError(null);

    if (editingVehicle) {
      await updateMutation.mutateAsync({
        vehicleId: editingVehicle.id,
        payload: {
          plate_number: normalizedPlate,
          make_model: form.make_model.trim(),
          year: form.year ? Number(form.year) : null,
          vin: normalizedVin,
          comment: form.comment.trim() || null
        }
      });
    } else {
      await createMutation.mutateAsync({
        client_id: form.client_id,
        plate_number: normalizedPlate,
        make_model: form.make_model.trim(),
        year: form.year ? Number(form.year) : null,
        vin: normalizedVin,
        comment: form.comment.trim() || null
      });
    }

    setModalOpen(false);
    setEditingVehicle(null);
    setForm(defaultVehicleForm());
  };

  const hasClients = (clientsQuery.data?.items?.length ?? 0) > 0;
  const clientOptions = useMemo(
    () =>
      (clientsQuery.data?.items ?? []).map((client) => ({
        value: client.id,
        label: `${client.name} (${formatPhoneForDisplay(client.phone)})`,
        keywords: [client.name, client.phone, client.email ?? ""]
      })),
    [clientsQuery.data?.items]
  );

  return (
    <PageLayout
      title={t("vehicles.title")}
      subtitle={t("vehicles.subtitle")}
      className="space-y-2"
      actions={
        <Button onClick={onOpenCreate} variant="primary">
          {t("vehicles.add")}
        </Button>
      }
    >
      <div className="space-y-2">
        <div className="flex flex-col gap-2 rounded-md border border-neutral-200 bg-neutral-0 p-2 md:flex-row md:items-center">
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("vehicles.search_placeholder")}
            className="min-w-0 md:flex-1"
          />
          <div className="flex items-center gap-2 md:w-auto">
            <Select
              size="sm"
              variant="subtle"
              value={sortMode}
              triggerLabel={t("vehicles.sort.label")}
              className="h-8 min-w-[180px]"
              onChange={(event) => setSortMode(event.target.value as VehicleSortMode)}
            >
              <option value="recent">{t("vehicles.sort.recent")}</option>
              <option value="plate">{t("vehicles.sort.plate")}</option>
              <option value="owner">{t("vehicles.sort.owner")}</option>
              <option value="history">{t("vehicles.sort.history")}</option>
            </Select>
            {hasAnyFilterActive ? (
              <Button size="sm" variant="ghost" className="h-8 px-2 text-neutral-500 hover:text-neutral-700" onClick={clearFilters}>
                {t("work_orders.toolbar.clear_filters")}
              </Button>
            ) : null}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          <RegistryStat label={t("vehicles.kpi.total")} value={totalVehicles} />
          <RegistryStat label={t("vehicles.kpi.active_orders")} value={summary.withActiveOrders} />
          <RegistryStat label={t("vehicles.kpi.without_orders")} value={summary.withoutOrders} />
          <RegistryStat label={t("vehicles.kpi.recent_added")} value={summary.recentAdded} />
        </div>

        <div className="space-y-1.5 md:hidden">
          {vehiclesQuery.isLoading ? (
            Array.from({ length: 4 }).map((_, index) => (
              <div key={`vehicle-skeleton-${index}`} className="h-[116px] rounded-md border border-neutral-200 bg-neutral-0 p-2.5">
                <div className="h-3 w-1/2 rounded bg-neutral-100" />
                <div className="mt-2 h-2.5 w-4/5 rounded bg-neutral-100" />
                <div className="mt-1.5 h-2.5 w-1/2 rounded bg-neutral-100" />
              </div>
            ))
          ) : vehiclesQuery.error ? (
            <div className="rounded-md border border-error/30 bg-error/5 p-2.5">
              <p className="text-sm text-error">{vehiclesQuery.error.message}</p>
              <Button className="mt-2" size="sm" variant="secondary" onClick={() => void vehiclesQuery.refetch()}>
                {t("datatable.retry")}
              </Button>
            </div>
          ) : visibleRows.length ? (
            visibleRows.map((vehicle) => {
              return (
                <article
                  key={vehicle.id}
                  className="w-full rounded-md border border-neutral-200 bg-neutral-0 p-2.5 transition-colors hover:border-neutral-300 hover:bg-neutral-50"
                >
                <button
                  type="button"
                  onClick={() => router.push(ROUTES.vehicleDetail(vehicle.id) as Route)}
                  className="w-full text-left"
                >
                  <p className="truncate text-sm font-semibold text-neutral-900">{vehicle.plate_number}</p>
                  <p className="mt-1 truncate text-xs text-neutral-600">
                    {vehicle.make_model}
                    {vehicle.year ? ` | ${vehicle.year}` : ""}
                  </p>
                  <p className="mt-1 truncate text-xs text-neutral-700">
                    {vehicle.client_name ? `${t("vehicles.table.client")}: ${vehicle.client_name}` : t("common.client")}
                  </p>
                  <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                    <Badge tone={(vehicle.active_work_order_count ?? 0) > 0 ? "warning" : "neutral"}>
                      {t("vehicles.table.orders_count_short", { count: vehicle.work_order_count ?? 0 })}
                    </Badge>
                    {vehicle.vin ? <Badge tone="neutral">VIN</Badge> : null}
                  </div>
                  <p className="mt-1 truncate text-[11px] text-neutral-500">
                    {vehicle.last_activity_at
                      ? t("vehicles.table.last_activity", { date: formatDateTime(vehicle.last_activity_at) })
                      : t("vehicles.table.no_history")}
                  </p>
                </button>
                <div className="mt-2 flex w-full items-center justify-end gap-1.5 border-t border-neutral-200 pt-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="primary"
                    className="h-8"
                    onClick={() => router.push(ROUTES.vehicleDetail(vehicle.id) as Route)}
                  >
                    {t("common.open")}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-8"
                    onClick={() => onOpenEdit(vehicle)}
                  >
                    {t("common.edit")}
                  </Button>
                </div>
              </article>
            );
            })
          ) : (
            <div className="rounded-md border border-neutral-200 bg-neutral-0 p-3 text-center">
              <p className="text-sm font-semibold text-neutral-900">{t("vehicles.empty.title")}</p>
              <p className="mt-1 text-xs text-neutral-600">{t("vehicles.empty.description")}</p>
              <Button className="mt-2" variant="primary" onClick={onOpenCreate}>
                {t("vehicles.add")}
              </Button>
            </div>
          )}
          <MobilePagination
            page={page}
            pageSize={PAGE_SIZE}
            total={totalVehicles}
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
            <div className="grid grid-cols-[minmax(0,1.9fr)_minmax(0,1.4fr)_minmax(0,1.2fr)_minmax(0,1.5fr)_minmax(0,1fr)_auto] gap-2 border-b border-neutral-200 bg-neutral-50 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-neutral-600">
              <div>{t("vehicles.table.vehicle")}</div>
              <div>{t("vehicles.table.client")}</div>
              <div>{t("vehicles.table.contact")}</div>
              <div>{t("vehicles.table.history")}</div>
              <div>{t("vehicles.table.last_update")}</div>
              <div className="text-right">{t("common.actions")}</div>
            </div>

            {vehiclesQuery.isLoading ? (
              <div className="space-y-2 p-3">
                {Array.from({ length: 5 }).map((_, index) => (
                  <div key={`vehicles-row-skeleton-${index}`} className="h-10 rounded-md bg-neutral-100" />
                ))}
              </div>
            ) : vehiclesQuery.error ? (
              <div className="p-3">
                <div className="rounded-md border border-error/30 bg-error/5 p-3">
                  <p className="text-sm text-error">{vehiclesQuery.error.message}</p>
                  <Button className="mt-2" size="sm" variant="secondary" onClick={() => void vehiclesQuery.refetch()}>
                    {t("datatable.retry")}
                  </Button>
                </div>
              </div>
            ) : visibleRows.length ? (
              <div>
                {visibleRows.map((vehicle) => {
                  return (
                    <div
                      key={vehicle.id}
                      className="grid grid-cols-[minmax(0,1.9fr)_minmax(0,1.4fr)_minmax(0,1.2fr)_minmax(0,1.5fr)_minmax(0,1fr)_auto] gap-2 border-b border-neutral-200 px-3 py-2.5 text-sm last:border-b-0 hover:bg-neutral-50"
                    >
                      <button type="button" className="min-w-0 text-left" onClick={() => router.push(ROUTES.vehicleDetail(vehicle.id) as Route)}>
                        <p className="truncate font-semibold text-primary">{vehicle.plate_number}</p>
                        <p className="truncate text-xs text-neutral-600">
                          {vehicle.make_model}
                          {vehicle.year ? ` · ${vehicle.year}` : ""}
                        </p>
                        <p className="truncate text-xs text-neutral-500">{vehicle.vin ? `${t("common.vin")}: ${vehicle.vin.slice(0, 8)}…` : t("common.not_set")}</p>
                      </button>

                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-neutral-900">{vehicle.client_name ?? t("common.unknown")}</p>
                        <p className="truncate text-xs text-neutral-600">{t("vehicles.table.owner")}</p>
                      </div>

                      <div className="min-w-0">
                        {vehicle.client_phone ? <p className="truncate text-sm text-neutral-900">{formatPhoneForDisplay(vehicle.client_phone)}</p> : null}
                        {vehicle.client_phone ? <p className="truncate text-xs text-neutral-600">{t("common.phone")}</p> : null}
                      </div>

                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-neutral-900">{t("vehicles.table.orders_count", { count: vehicle.work_order_count ?? 0 })}</p>
                        <p className="truncate text-xs text-neutral-600">
                          {vehicle.last_activity_at
                            ? t("vehicles.table.last_activity", { date: formatDateTime(vehicle.last_activity_at) })
                            : t("vehicles.table.no_history")}
                        </p>
                        {(vehicle.active_work_order_count ?? 0) > 0 ? (
                          <p className="text-xs font-medium text-warning">
                            {t("vehicles.table.active_orders", { count: vehicle.active_work_order_count ?? 0 })}
                          </p>
                        ) : null}
                      </div>

                      <div className="text-xs text-neutral-600">{formatDateTime(vehicle.updated_at)}</div>

                      <div className="flex items-center justify-end gap-1.5">
                        <Button size="sm" variant="secondary" onClick={() => router.push(ROUTES.vehicleDetail(vehicle.id) as Route)}>{t("common.open")}</Button>
                        <Button size="sm" variant="ghost" onClick={() => onOpenEdit(vehicle)}>{t("common.edit")}</Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-3">
                <div className="rounded-md border border-neutral-200 bg-neutral-50 px-4 py-6 text-center">
                  <p className="text-sm font-semibold text-neutral-900">{t("vehicles.empty.title")}</p>
                  <p className="mt-1 text-sm text-neutral-600">{t("vehicles.empty.description")}</p>
                  <Button className="mt-3" variant="primary" onClick={onOpenCreate}>
                    {t("vehicles.add")}
                  </Button>
                </div>
              </div>
            )}

            {totalVehicles > 0 ? (
              <div className="border-t border-neutral-200 bg-neutral-50 px-3 py-2">
                <MobilePagination
                  page={page}
                  pageSize={PAGE_SIZE}
                  total={totalVehicles}
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
        title={editingVehicle ? t("vehicles.modal.edit_title") : t("vehicles.modal.create_title")}
        description={t("vehicles.modal.description")}
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              type="submit"
              form="vehicle-form"
              loading={createMutation.isPending || updateMutation.isPending}
              disabled={!editingVehicle && !hasClients}
            >
              {editingVehicle ? t("common.save") : t("common.create")}
            </Button>
          </FormActions>
        }
      >
        <form id="vehicle-form" className="space-y-2" onSubmit={(event) => void onSubmit(event)}>
          {!editingVehicle ? (
            <FormField id="client-id" label={t("common.client")} required>
              <Combobox
                id="client-id"
                value={form.client_id}
                onChange={(value) => setForm((prev) => ({ ...prev, client_id: value }))}
                disabled={clientsQuery.isLoading || !hasClients}
                options={clientOptions}
                placeholder={clientsQuery.isLoading ? t("vehicles.form.loading_clients") : t("vehicles.form.select_client")}
                searchPlaceholder={t("common.search")}
                emptyText={t("vehicles.form.no_clients")}
                size="md"
              />
              {!clientsQuery.isLoading && !hasClients ? (
                <p className="mt-1 text-xs text-neutral-600">{t("vehicles.form.no_clients")}</p>
              ) : null}
              {clientsQuery.error ? <p className="mt-1 text-xs text-error">{t("vehicles.form.load_clients_error")}</p> : null}
            </FormField>
          ) : null}
          <FormField id="plate-number" label={t("common.plate_number")} required>
            <Input
              id="plate-number"
              value={form.plate_number}
              onChange={(event) => setForm((prev) => ({ ...prev, plate_number: event.target.value }))}
            />
          </FormField>
          <FormField id="make-model" label={t("common.make_model")} required>
            <Input
              id="make-model"
              value={form.make_model}
              onChange={(event) => setForm((prev) => ({ ...prev, make_model: event.target.value }))}
            />
          </FormField>
          <FormField id="year" label={t("common.year")}>
            <Input id="year" value={form.year} onChange={(event) => setForm((prev) => ({ ...prev, year: event.target.value }))} />
          </FormField>
          <FormField id="vin" label={t("common.vin")}>
            <Input id="vin" value={form.vin} onChange={(event) => setForm((prev) => ({ ...prev, vin: event.target.value }))} />
          </FormField>
          <FormField id="comment" label={t("common.comment")}>
            <Textarea
              id="comment"
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
