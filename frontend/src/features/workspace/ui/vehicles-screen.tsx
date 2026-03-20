"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import { formatPhoneForDisplay } from "@/core/lib/phone";
import { DataTable } from "@/design-system/primitives/data-table/data-table";
import type { DataTableColumn } from "@/design-system/primitives/data-table/data-table.types";
import { Button, FormActions, FormField, Input, Modal, Textarea } from "@/design-system/primitives";
import { PageLayout, Section, Toolbar } from "@/design-system/patterns";
import {
  createVehicle,
  fetchClients,
  fetchVehicles,
  mvpQueryKeys,
  updateVehicle
} from "@/features/workspace/api/mvp-api";
import type { VehicleRecord } from "@/features/workspace/types/mvp-types";

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

  const vehiclesQuery = useQuery({
    queryKey: mvpQueryKeys.vehicles(q, "", PAGE_SIZE, offset),
    queryFn: () => fetchVehicles({ q, limit: PAGE_SIZE, offset }),
    placeholderData: keepPreviousData
  });

  const clientsQuery = useQuery({
    queryKey: mvpQueryKeys.clients("", 100, 0),
    queryFn: () => fetchClients({ limit: 100, offset: 0 })
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
        id: "plate",
        header: "Plate",
        minWidth: 150,
        cell: (row) => (
          <Link href={ROUTES.vehicleDetail(row.id) as Route} className="font-medium text-primary hover:underline">
            {row.plate_number}
          </Link>
        )
      },
      {
        id: "model",
        header: "Make/Model",
        minWidth: 220,
        cell: (row) => row.make_model
      },
      {
        id: "client",
        header: "Client",
        minWidth: 220,
        cell: (row) => clientsMap.get(row.client_id) ?? row.client_id
      },
      {
        id: "year",
        header: "Year",
        minWidth: 90,
        cell: (row) => (row.year ? String(row.year) : "-")
      }
    ],
    [clientsMap]
  );

  const onOpenCreate = (): void => {
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
    if (!form.plate_number.trim() || !form.make_model.trim()) {
      setFormError("Plate number and make/model are required.");
      return;
    }
    if (!editingVehicle && !form.client_id) {
      setFormError("Client is required for new vehicle.");
      return;
    }
    setFormError(null);

    if (editingVehicle) {
      await updateMutation.mutateAsync({
        vehicleId: editingVehicle.id,
        payload: {
          plate_number: form.plate_number.trim(),
          make_model: form.make_model.trim(),
          year: form.year ? Number(form.year) : null,
          vin: form.vin.trim() || null,
          comment: form.comment.trim() || null
        }
      });
    } else {
      await createMutation.mutateAsync({
        client_id: form.client_id,
        plate_number: form.plate_number.trim(),
        make_model: form.make_model.trim(),
        year: form.year ? Number(form.year) : null,
        vin: form.vin.trim() || null,
        comment: form.comment.trim() || null
      });
    }

    setModalOpen(false);
    setEditingVehicle(null);
    setForm(defaultVehicleForm());
  };

  return (
    <PageLayout title="Vehicles" subtitle="Vehicle cards and service history linkage">
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
              <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by plate or model" />
              <Button type="submit" variant="secondary">
                Search
              </Button>
            </form>
          }
          trailing={
            <Button onClick={onOpenCreate} variant="primary">
              Add vehicle
            </Button>
          }
        />
      </Section>

      <Section>
        <DataTable
          columns={columns}
          rows={rows}
          getRowId={(row) => row.id}
          loading={vehiclesQuery.isLoading}
          error={vehiclesQuery.error?.message}
          onRetry={() => void vehiclesQuery.refetch()}
          emptyTitle="No vehicles"
          emptyDescription="Add a vehicle to link it with work orders."
          rowActions={[
            {
              id: "open",
              label: "Details",
              onClick: (row) => {
                router.push(ROUTES.vehicleDetail(row.id) as Route);
              }
            },
            {
              id: "edit",
              label: "Edit",
              variant: "secondary",
              onClick: onOpenEdit
            }
          ]}
          pagination={{
            page,
            pageSize: PAGE_SIZE,
            total: vehiclesQuery.data?.total ?? 0,
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
        title={editingVehicle ? "Edit vehicle" : "Create vehicle"}
        description="Vehicle is a first-class entity linked to client and work orders"
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="vehicle-form" loading={createMutation.isPending || updateMutation.isPending}>
              {editingVehicle ? "Save" : "Create"}
            </Button>
          </FormActions>
        }
      >
        <form id="vehicle-form" className="space-y-2" onSubmit={(event) => void onSubmit(event)}>
          {!editingVehicle ? (
            <FormField id="client-id" label="Client" required>
              <select
                id="client-id"
                className="h-5 w-full rounded-sm border border-neutral-300 bg-neutral-0 px-2 text-sm text-neutral-900"
                value={form.client_id}
                onChange={(event) => setForm((prev) => ({ ...prev, client_id: event.target.value }))}
              >
                <option value="">Select client</option>
                {(clientsQuery.data?.items ?? []).map((client) => (
                  <option key={client.id} value={client.id}>
                    {client.name} ({formatPhoneForDisplay(client.phone)})
                  </option>
                ))}
              </select>
            </FormField>
          ) : null}
          <FormField id="plate-number" label="Plate number" required>
            <Input
              id="plate-number"
              value={form.plate_number}
              onChange={(event) => setForm((prev) => ({ ...prev, plate_number: event.target.value }))}
            />
          </FormField>
          <FormField id="make-model" label="Make / model" required>
            <Input
              id="make-model"
              value={form.make_model}
              onChange={(event) => setForm((prev) => ({ ...prev, make_model: event.target.value }))}
            />
          </FormField>
          <FormField id="year" label="Year">
            <Input id="year" value={form.year} onChange={(event) => setForm((prev) => ({ ...prev, year: event.target.value }))} />
          </FormField>
          <FormField id="vin" label="VIN">
            <Input id="vin" value={form.vin} onChange={(event) => setForm((prev) => ({ ...prev, vin: event.target.value }))} />
          </FormField>
          <FormField id="comment" label="Comment">
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
