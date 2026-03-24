"use client";

import type { Route } from "next";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import { formatPhoneForDisplay, normalizePhoneForSubmit } from "@/core/lib/phone";
import { cn } from "@/core/lib/utils";
import { normalizePlateForSubmit, normalizeVinForSubmit } from "@/core/lib/vehicle";
import { Button, Combobox, FormField, Input, PhoneInput, Select, Textarea } from "@/design-system/primitives";
import { PageLayout } from "@/design-system/patterns";
import { createClient, createVehicle, createWorkOrder, fetchClients, fetchEmployees, fetchVehicles, mvpQueryKeys } from "@/features/workspace/api/mvp-api";

const LOOKUP_LIMIT = 50;

type IntakeMode = "select" | "create";

type CreateWorkOrderForm = {
  client_id: string;
  vehicle_id: string;
  assigned_employee_id: string;
  description: string;
  total_amount: string;
};

type NewClientForm = {
  name: string;
  phone: string;
  email: string;
  source: string;
  comment: string;
};

type NewVehicleForm = {
  plate_number: string;
  make_model: string;
  year: string;
  vin: string;
  comment: string;
};

function defaultWorkOrderForm(): CreateWorkOrderForm {
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
    source: "",
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

export function WorkOrderIntakeScreen(): JSX.Element {
  const router = useRouter();
  const queryClient = useQueryClient();
  const vehicleSectionRef = useRef<HTMLElement | null>(null);
  const workOrderSectionRef = useRef<HTMLElement | null>(null);
  const prevClientIdRef = useRef("");
  const prevVehicleIdRef = useRef("");

  const [clientMode, setClientMode] = useState<IntakeMode>("select");
  const [vehicleMode, setVehicleMode] = useState<IntakeMode>("select");
  const [workOrderForm, setWorkOrderForm] = useState<CreateWorkOrderForm>(defaultWorkOrderForm());
  const [newClientForm, setNewClientForm] = useState<NewClientForm>(defaultNewClientForm());
  const [newVehicleForm, setNewVehicleForm] = useState<NewVehicleForm>(defaultNewVehicleForm());
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    const previousClientId = prevClientIdRef.current;
    if (!previousClientId && workOrderForm.client_id) {
      vehicleSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    prevClientIdRef.current = workOrderForm.client_id;
  }, [workOrderForm.client_id]);

  useEffect(() => {
    const previousVehicleId = prevVehicleIdRef.current;
    if (!previousVehicleId && workOrderForm.vehicle_id) {
      workOrderSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    prevVehicleIdRef.current = workOrderForm.vehicle_id;
  }, [workOrderForm.vehicle_id]);

  const clientsLookupQuery = useQuery({
    queryKey: mvpQueryKeys.clients("", LOOKUP_LIMIT, 0),
    queryFn: () => fetchClients({ limit: LOOKUP_LIMIT, offset: 0 })
  });

  const vehiclesByClientQuery = useQuery({
    queryKey: mvpQueryKeys.vehicles("", workOrderForm.client_id, LOOKUP_LIMIT, 0),
    queryFn: () =>
      fetchVehicles({
        client_id: workOrderForm.client_id || undefined,
        limit: LOOKUP_LIMIT,
        offset: 0
      }),
    enabled: Boolean(workOrderForm.client_id)
  });

  const employeesQuery = useQuery({
    queryKey: mvpQueryKeys.employees("", "", LOOKUP_LIMIT, 0),
    queryFn: () => fetchEmployees({ limit: LOOKUP_LIMIT, offset: 0 })
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

  const createWorkOrderMutation = useMutation({
    mutationFn: createWorkOrder,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["work-orders"] });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.dashboardSummary });
    }
  });

  const clientOptions = useMemo(
    () =>
      (clientsLookupQuery.data?.items ?? []).map((client) => ({
        value: client.id,
        label: `${client.name} (${formatPhoneForDisplay(client.phone)})`,
        keywords: [client.phone, client.email ?? ""]
      })),
    [clientsLookupQuery.data?.items]
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

  const onCreateClientInline = async (): Promise<void> => {
    const name = newClientForm.name.trim();
    const phone = normalizePhoneForSubmit(newClientForm.phone);
    const email = newClientForm.email.trim();
    const source = newClientForm.source.trim();
    const comment = newClientForm.comment.trim();

    if (!name || !phone) {
      setFormError("Client name and phone are required.");
      return;
    }

    // Guard against duplicate client creation by phone before submit.
    try {
      const lookup = await fetchClients({ q: phone, limit: 20, offset: 0 });
      const duplicate = lookup.items.find((item) => item.phone === phone);
      if (duplicate) {
        setFormError(`Client with this phone already exists: ${duplicate.name}. Select it in step 1.`);
        setClientMode("select");
        setWorkOrderForm((prev) => ({ ...prev, client_id: duplicate.id, vehicle_id: "" }));
        return;
      }
    } catch {
      // Do not block form submit if precheck fails; backend remains the source of truth.
    }

    setFormError(null);
    const createdClient = await createClientMutation.mutateAsync({
      name,
      phone,
      email: email || null,
      source: source || null,
      comment: comment || null
    });

    setWorkOrderForm((prev) => ({
      ...prev,
      client_id: createdClient.id,
      vehicle_id: ""
    }));
    setClientMode("select");
    setVehicleMode("create");
    setNewClientForm(defaultNewClientForm());
  };

  const onCreateVehicleInline = async (): Promise<void> => {
    if (!workOrderForm.client_id) {
      setFormError("Select or create a client first.");
      return;
    }

    const plateNumber = normalizePlateForSubmit(newVehicleForm.plate_number);
    const makeModel = newVehicleForm.make_model.trim();
    if (!plateNumber || !makeModel) {
      setFormError("Plate number and make/model are required.");
      return;
    }

    const year = newVehicleForm.year.trim();
    const vin = normalizeVinForSubmit(newVehicleForm.vin);
    const comment = newVehicleForm.comment.trim();

    // Guard against duplicate plate/vin before submit.
    try {
      const plateLookup = await fetchVehicles({ q: plateNumber, limit: 50, offset: 0 });
      const duplicatePlate = plateLookup.items.find((item) => normalizePlateForSubmit(item.plate_number) === plateNumber);
      if (duplicatePlate) {
        setFormError(`Vehicle with this plate already exists (${duplicatePlate.plate_number}). Select it in step 2.`);
        setVehicleMode("select");
        setWorkOrderForm((prev) => ({ ...prev, vehicle_id: duplicatePlate.id }));
        return;
      }

      if (vin) {
        const vinLookup = await fetchVehicles({ q: vin, limit: 50, offset: 0 });
        const duplicateVin = vinLookup.items.find((item) => normalizeVinForSubmit(item.vin) === vin);
        if (duplicateVin) {
          setFormError(`Vehicle with this VIN already exists (${duplicateVin.plate_number}). Select it in step 2.`);
          setVehicleMode("select");
          setWorkOrderForm((prev) => ({ ...prev, vehicle_id: duplicateVin.id }));
          return;
        }
      }
    } catch {
      // Do not block submit if precheck fails; backend remains source of truth.
    }

    setFormError(null);
    const createdVehicle = await createVehicleMutation.mutateAsync({
      client_id: workOrderForm.client_id,
      plate_number: plateNumber,
      make_model: makeModel,
      year: year ? Number(year) : null,
      vin,
      comment: comment || null
    });

    setWorkOrderForm((prev) => ({
      ...prev,
      vehicle_id: createdVehicle.id
    }));
    setVehicleMode("select");
    setNewVehicleForm(defaultNewVehicleForm());
  };

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!workOrderForm.client_id || !workOrderForm.vehicle_id || !workOrderForm.description.trim()) {
      setFormError("Client, vehicle and description are required.");
      return;
    }

    const total = Number(workOrderForm.total_amount);
    if (!Number.isFinite(total) || total <= 0) {
      setFormError("Total amount must be greater than 0.");
      return;
    }

    setFormError(null);
    const created = await createWorkOrderMutation.mutateAsync({
      client_id: workOrderForm.client_id,
      vehicle_id: workOrderForm.vehicle_id,
      description: workOrderForm.description.trim(),
      total_amount: total,
      assigned_employee_id: workOrderForm.assigned_employee_id || null,
      status: "new"
    });

    router.push(ROUTES.workOrderDetail(created.id) as Route);
  };

  const isBusy = createClientMutation.isPending || createVehicleMutation.isPending || createWorkOrderMutation.isPending;
  const isVehicleStepActive = Boolean(workOrderForm.client_id);
  const isWorkOrderStepActive = Boolean(workOrderForm.vehicle_id);

  return (
    <PageLayout
      title="New work order"
      subtitle="Client -> Vehicle -> Work order"
      className="space-y-2"
      actions={
        <Button type="button" size="sm" variant="secondary" onClick={() => router.push(ROUTES.workOrders as Route)}>
          Back to work orders
        </Button>
      }
    >
      <form className="mx-auto w-full max-w-[960px] space-y-2 pb-14" onSubmit={(event) => void onSubmit(event)}>
        <section className="space-y-1.5 border-b border-neutral-200 pb-3">
          <div className="flex flex-wrap items-center justify-between gap-1.5">
            <p className="flex items-center gap-1.5 text-sm font-semibold text-neutral-900">
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-neutral-300 text-[11px] font-semibold text-neutral-700">
                1
              </span>
              Client
            </p>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="h-7 px-2 text-xs text-neutral-600"
              onClick={() => {
                setClientMode((prev) => (prev === "select" ? "create" : "select"));
                setFormError(null);
              }}
            >
              {clientMode === "select" ? "Create new client" : "Use existing client"}
            </Button>
          </div>

          {clientMode === "select" ? (
            <div className="grid grid-cols-1 gap-1.5">
              <FormField id="client_id" label="Client" required>
                <Combobox
                  id="client_id"
                  size="sm"
                  value={workOrderForm.client_id}
                  onChange={(value) => {
                    setWorkOrderForm((prev) => ({
                      ...prev,
                      client_id: value,
                      vehicle_id: ""
                    }));
                    setVehicleMode("select");
                  }}
                  options={clientOptions}
                  placeholder="Select client"
                  searchPlaceholder="Search client"
                  emptyText={clientsLookupQuery.isLoading ? "Loading clients..." : "No clients found"}
                />
              </FormField>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="grid grid-cols-1 gap-1.5 md:grid-cols-2">
                <FormField id="new-client-name" label="Client name" required>
                  <Input
                    fullHeight="sm"
                    id="new-client-name"
                    value={newClientForm.name}
                    onChange={(event) => setNewClientForm((prev) => ({ ...prev, name: event.target.value }))}
                  />
                </FormField>
                <FormField id="new-client-phone" label="Phone" required>
                  <PhoneInput
                    fullHeight="sm"
                    id="new-client-phone"
                    value={newClientForm.phone}
                    onChange={(value) => setNewClientForm((prev) => ({ ...prev, phone: value }))}
                  />
                </FormField>
                <FormField id="new-client-email" label="Email">
                  <Input
                    fullHeight="sm"
                    id="new-client-email"
                    type="email"
                    value={newClientForm.email}
                    onChange={(event) => setNewClientForm((prev) => ({ ...prev, email: event.target.value }))}
                  />
                </FormField>
                <FormField id="new-client-source" label="Откуда пришел клиент">
                  <Input
                    fullHeight="sm"
                    id="new-client-source"
                    value={newClientForm.source}
                    onChange={(event) => setNewClientForm((prev) => ({ ...prev, source: event.target.value }))}
                  />
                </FormField>
                <FormField id="new-client-comment" label="Comment">
                  <Input
                    fullHeight="sm"
                    id="new-client-comment"
                    value={newClientForm.comment}
                    onChange={(event) => setNewClientForm((prev) => ({ ...prev, comment: event.target.value }))}
                  />
                </FormField>
              </div>
              <div className="flex justify-end pt-0.5">
                <Button type="button" size="sm" variant="secondary" loading={createClientMutation.isPending} onClick={() => void onCreateClientInline()}>
                  Create client and continue
                </Button>
              </div>
            </div>
          )}
        </section>

        <section
          ref={vehicleSectionRef}
          aria-disabled={!isVehicleStepActive}
          className={cn("space-y-1.5 border-b border-neutral-200 pb-3 transition-opacity", !isVehicleStepActive && "opacity-50")}
        >
          <div className="flex flex-wrap items-center justify-between gap-1.5">
            <p className="flex items-center gap-1.5 text-sm font-semibold text-neutral-900">
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-neutral-300 text-[11px] font-semibold text-neutral-700">
                2
              </span>
              Vehicle
            </p>
            {isVehicleStepActive ? (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="h-7 px-2 text-xs text-neutral-600"
                onClick={() => {
                  setVehicleMode((prev) => (prev === "select" ? "create" : "select"));
                  setFormError(null);
                }}
              >
                {vehicleMode === "select" ? "Create new vehicle" : "Use existing vehicle"}
              </Button>
            ) : null}
          </div>

          {!isVehicleStepActive ? (
            <p className="text-xs text-neutral-600">Complete step 1 to unlock this section.</p>
          ) : vehicleMode === "select" ? (
            <div className="grid grid-cols-1 gap-1.5">
              <FormField id="vehicle_id" label="Vehicle" required>
                <Combobox
                  id="vehicle_id"
                  size="sm"
                  value={workOrderForm.vehicle_id}
                  onChange={(value) => setWorkOrderForm((prev) => ({ ...prev, vehicle_id: value }))}
                  options={vehicleOptions}
                  placeholder="Select vehicle"
                  searchPlaceholder="Search vehicle"
                  emptyText={vehiclesByClientQuery.isLoading ? "Loading vehicles..." : "No vehicles found for this client"}
                />
              </FormField>
            </div>
          ) : (
            <div className="space-y-1.5">
              <div className="grid grid-cols-1 gap-1.5 md:grid-cols-2">
                <FormField id="new-vehicle-plate" label="Plate number" required>
                  <Input
                    fullHeight="sm"
                    id="new-vehicle-plate"
                    value={newVehicleForm.plate_number}
                    onChange={(event) => setNewVehicleForm((prev) => ({ ...prev, plate_number: event.target.value }))}
                  />
                </FormField>
                <FormField id="new-vehicle-model" label="Make / model" required>
                  <Input
                    fullHeight="sm"
                    id="new-vehicle-model"
                    value={newVehicleForm.make_model}
                    onChange={(event) => setNewVehicleForm((prev) => ({ ...prev, make_model: event.target.value }))}
                  />
                </FormField>
                <FormField id="new-vehicle-year" label="Year">
                  <Input
                    fullHeight="sm"
                    id="new-vehicle-year"
                    value={newVehicleForm.year}
                    onChange={(event) => setNewVehicleForm((prev) => ({ ...prev, year: event.target.value }))}
                  />
                </FormField>
                <FormField id="new-vehicle-vin" label="VIN">
                  <Input
                    fullHeight="sm"
                    id="new-vehicle-vin"
                    value={newVehicleForm.vin}
                    onChange={(event) => setNewVehicleForm((prev) => ({ ...prev, vin: event.target.value }))}
                  />
                </FormField>
              </div>
              <FormField id="new-vehicle-comment" label="Comment">
                <Input
                  fullHeight="sm"
                  id="new-vehicle-comment"
                  value={newVehicleForm.comment}
                  onChange={(event) => setNewVehicleForm((prev) => ({ ...prev, comment: event.target.value }))}
                />
              </FormField>
              <div className="flex justify-end pt-0.5">
                <Button type="button" size="sm" variant="secondary" loading={createVehicleMutation.isPending} onClick={() => void onCreateVehicleInline()}>
                  Create vehicle and continue
                </Button>
              </div>
            </div>
          )}
        </section>

        <section
          ref={workOrderSectionRef}
          aria-disabled={!isWorkOrderStepActive}
          className={cn("grid grid-cols-1 gap-1.5 pb-3 transition-opacity md:grid-cols-2", !isWorkOrderStepActive && "opacity-50")}
        >
          <p className="flex items-center gap-1.5 text-sm font-semibold text-neutral-900 md:col-span-2">
            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-neutral-300 text-[11px] font-semibold text-neutral-700">
              3
            </span>
            Work order
          </p>

          {!isWorkOrderStepActive ? (
            <p className="text-xs text-neutral-600 md:col-span-2">Complete step 2 to unlock this section.</p>
          ) : (
            <>
              <FormField id="assigned_employee_id" label="Assignee (optional)" className="md:col-span-2">
                <Select
                  className="h-8"
                  id="assigned_employee_id"
                  value={workOrderForm.assigned_employee_id}
                  onChange={(event) => setWorkOrderForm((prev) => ({ ...prev, assigned_employee_id: event.target.value }))}
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
                  fullHeight="sm"
                  id="total_amount"
                  value={workOrderForm.total_amount}
                  onChange={(event) => setWorkOrderForm((prev) => ({ ...prev, total_amount: event.target.value }))}
                  placeholder="0.00"
                />
              </FormField>
              <FormField id="description" label="Description" required>
                <Textarea
                  className="min-h-24"
                  id="description"
                  value={workOrderForm.description}
                  onChange={(event) => setWorkOrderForm((prev) => ({ ...prev, description: event.target.value }))}
                />
              </FormField>
            </>
          )}
        </section>

        {formError ? <p className="text-xs text-error">{formError}</p> : null}
        {clientsLookupQuery.error ? <p className="text-xs text-error">{clientsLookupQuery.error.message}</p> : null}
        {vehiclesByClientQuery.error ? <p className="text-xs text-error">{vehiclesByClientQuery.error.message}</p> : null}
        {createClientMutation.error ? <p className="text-xs text-error">{createClientMutation.error.message}</p> : null}
        {createVehicleMutation.error ? <p className="text-xs text-error">{createVehicleMutation.error.message}</p> : null}
        {createWorkOrderMutation.error ? <p className="text-xs text-error">{createWorkOrderMutation.error.message}</p> : null}

        <div className="sticky bottom-0 z-10 -mx-1 mt-1 bg-gradient-to-t from-neutral-100/95 via-neutral-100/92 to-transparent px-1 pt-3">
          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-neutral-200 py-2">
            <Button type="button" size="sm" variant="secondary" onClick={() => router.push(ROUTES.workOrders as Route)}>
              Cancel
            </Button>
            <Button type="submit" size="sm" variant="primary" loading={createWorkOrderMutation.isPending} disabled={isBusy}>
              Create work order
            </Button>
          </div>
        </div>
      </form>
    </PageLayout>
  );
}
