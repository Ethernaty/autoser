"use client";

import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import { formatPhoneForDisplay } from "@/core/lib/phone";
import { normalizePlateForSubmit, normalizeVinForSubmit } from "@/core/lib/vehicle";
import { DataTable } from "@/design-system/primitives/data-table/data-table";
import type { DataTableColumn } from "@/design-system/primitives/data-table/data-table.types";
import { Button, Combobox, FormActions, FormField, Input, Modal, Textarea } from "@/design-system/primitives";
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

  const rows = vehiclesQuery.data?.items ?? [];
  const clientsMap = useMemo(() => {
    const map = new Map<string, string>();
    (clientsQuery.data?.items ?? []).forEach((client) => {
      map.set(client.id, client.name);
    });
    return map;
  }, [clientsQuery.data?.items]);

  const columns = useMemo<DataTableColumn<VehicleRecord>[]>(
    () => [
      {
        id: "vehicle",
        header: t("vehicles.table.vehicle"),
        minWidth: 340,
        cell: (row) => (
          <div className="space-y-0.5">
            <p className="font-semibold text-neutral-900">{row.plate_number}</p>
            <p className="text-xs text-neutral-600">
              {row.make_model}
              {row.year ? ` | ${row.year}` : ""}
            </p>
          </div>
        )
      },
      {
        id: "client",
        header: t("vehicles.table.client"),
        minWidth: 240,
        cell: (row) => clientsMap.get(row.client_id) ?? row.client_id
      }
    ],
    [clientsMap, t]
  );

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
      <div className="space-y-1.5">
        <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t("vehicles.search_placeholder")} />

        <DataTable
          columns={columns}
          rows={rows}
          getRowId={(row) => row.id}
          onRowClick={(row) => {
            router.push(ROUTES.vehicleDetail(row.id) as Route);
          }}
          loading={vehiclesQuery.isLoading}
          error={vehiclesQuery.error?.message}
          onRetry={() => void vehiclesQuery.refetch()}
          emptyTitle={t("vehicles.empty.title")}
          emptyDescription={t("vehicles.empty.description")}
          emptyAction={
            <Button variant="primary" onClick={onOpenCreate}>
              {t("vehicles.add")}
            </Button>
          }
          rowActions={[
            {
              id: "edit",
              label: t("common.edit"),
              variant: "secondary",
              onClick: onOpenEdit
            }
          ]}
          tableClassName="min-w-full"
          pagination={
            (vehiclesQuery.data?.total ?? 0) > 0
              ? {
                  page,
                  pageSize: PAGE_SIZE,
                  total: vehiclesQuery.data?.total ?? 0,
                  onPageChange: (nextPage) => {
                    setPage(nextPage);
                    updateUrlState({ q, page: nextPage });
                  }
                }
              : undefined
          }
        />
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
