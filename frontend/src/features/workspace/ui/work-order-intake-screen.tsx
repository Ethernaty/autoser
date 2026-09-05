"use client";

import type { Route } from "next";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import { formatPhoneForDisplay, normalizePhoneForSubmit } from "@/core/lib/phone";
import { cn } from "@/core/lib/utils";
import { normalizePlateForSubmit, normalizeVinForSubmit } from "@/core/lib/vehicle";
import { Button, Combobox, FormField, Input, PhoneInput, Select, Textarea } from "@/design-system/primitives";
import { PageLayout } from "@/design-system/patterns";
import { createClient, createVehicle, createWorkOrder, fetchClients, fetchEmployees, fetchVehicles, mvpQueryKeys } from "@/features/workspace/api/mvp-api";
import { useI18n } from "@/shared/i18n";

const LOOKUP_LIMIT = 50;

type IntakeMode = "select" | "create";
type IntakePhoto = { name: string; content_type: "image/png" | "image/jpeg" | "image/webp"; data_url: string };

type CreateWorkOrderForm = {
  client_id: string;
  vehicle_id: string;
  assigned_employee_id: string;
  description: string;
  diagnosis: string;
  mileage: string;
  due_at: string;
  estimated_amount: string;
  intake_notes: string;
};

type NewClientForm = {
  name: string;
  phone: string;
  email: string;
};

type NewVehicleForm = {
  plate_number: string;
  make_model: string;
  year: string;
  vin: string;
};

function defaultWorkOrderForm(): CreateWorkOrderForm {
  return {
    client_id: "",
    vehicle_id: "",
    assigned_employee_id: "",
    description: "",
    diagnosis: "",
    mileage: "",
    due_at: "",
    estimated_amount: "",
    intake_notes: ""
  };
}

function defaultNewClientForm(): NewClientForm {
  return {
    name: "",
    phone: "",
    email: ""
  };
}

function defaultNewVehicleForm(): NewVehicleForm {
  return {
    plate_number: "",
    make_model: "",
    year: "",
    vin: ""
  };
}

const KNOWN_EMPLOYEE_ROLES = ["owner", "admin", "manager", "employee"] as const;
type KnownEmployeeRole = (typeof KNOWN_EMPLOYEE_ROLES)[number];

function normalizeRoleValue(rawRole: string | null | undefined): KnownEmployeeRole | null {
  if (!rawRole) return null;
  const normalized = rawRole.trim().toLowerCase().replace(/[^a-z_]/g, "");
  return (KNOWN_EMPLOYEE_ROLES as readonly string[]).includes(normalized) ? (normalized as KnownEmployeeRole) : null;
}

function employeeRoleLabel(rawRole: string | null | undefined, t: (key: string) => string): string {
  const normalized = normalizeRoleValue(rawRole);
  if (normalized) {
    return t(`employees.role.${normalized}`);
  }
  return (rawRole ?? "").replace(/[,\s]+$/g, "").trim() || t("employees.role.employee");
}

export function WorkOrderIntakeScreen(): JSX.Element {
  const { t } = useI18n();
  const router = useRouter();
  const searchParams = useSearchParams();
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
  const [clientSearch, setClientSearch] = useState("");
  const [draftRestored, setDraftRestored] = useState(false);
  const [photos, setPhotos] = useState<IntakePhoto[]>([]);

  useEffect(() => {
    const preselectedClient = searchParams.get("client_id") ?? "";
    const preselectedVehicle = searchParams.get("vehicle_id") ?? "";
    const saved = window.sessionStorage.getItem("autoservice:intake-draft");
    if (saved) {
      try {
        setWorkOrderForm({ ...defaultWorkOrderForm(), ...JSON.parse(saved) });
        setDraftRestored(true);
      } catch {
        window.sessionStorage.removeItem("autoservice:intake-draft");
      }
    }
    if (preselectedClient || preselectedVehicle) {
      setWorkOrderForm((current) => ({
        ...current,
        client_id: preselectedClient || current.client_id,
        vehicle_id: preselectedVehicle || current.vehicle_id
      }));
    }
  }, [searchParams]);

  useEffect(() => {
    const hasDraft = Object.values(workOrderForm).some(Boolean);
    if (hasDraft) window.sessionStorage.setItem("autoservice:intake-draft", JSON.stringify(workOrderForm));
    const warn = (event: BeforeUnloadEvent): void => {
      if (!hasDraft) return;
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [workOrderForm]);

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
    queryKey: mvpQueryKeys.clients(clientSearch, LOOKUP_LIMIT, 0),
    queryFn: () => fetchClients({ q: clientSearch, limit: LOOKUP_LIMIT, offset: 0 })
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

    if (!name || !phone) {
      setFormError(t("work_order_intake.error.client_required"));
      return;
    }

    try {
      const lookup = await fetchClients({ q: phone, limit: 20, offset: 0 });
      const duplicate = lookup.items.find((item) => item.phone === phone);
      if (duplicate) {
        setFormError(t("work_order_intake.error.client_duplicate", { name: duplicate.name }));
        setClientMode("select");
        setWorkOrderForm((prev) => ({ ...prev, client_id: duplicate.id, vehicle_id: "" }));
        return;
      }
    } catch {
      // backend remains source of truth
    }

    setFormError(null);
    const createdClient = await createClientMutation.mutateAsync({
      name,
      phone,
      email: email || null
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
      setFormError(t("work_order_intake.error.select_client_first"));
      return;
    }

    const plateNumber = normalizePlateForSubmit(newVehicleForm.plate_number);
    const makeModel = newVehicleForm.make_model.trim();
    if (!plateNumber || !makeModel) {
      setFormError(t("work_order_intake.error.vehicle_required"));
      return;
    }

    const year = newVehicleForm.year.trim();
    const vin = normalizeVinForSubmit(newVehicleForm.vin);

    try {
      const plateLookup = await fetchVehicles({ q: plateNumber, limit: 50, offset: 0 });
      const duplicatePlate = plateLookup.items.find((item) => normalizePlateForSubmit(item.plate_number) === plateNumber);
      if (duplicatePlate) {
        setFormError(t("work_order_intake.error.vehicle_duplicate_plate", { plate: duplicatePlate.plate_number }));
        setVehicleMode("select");
        setWorkOrderForm((prev) => ({ ...prev, vehicle_id: duplicatePlate.id }));
        return;
      }

      if (vin) {
        const vinLookup = await fetchVehicles({ q: vin, limit: 50, offset: 0 });
        const duplicateVin = vinLookup.items.find((item) => normalizeVinForSubmit(item.vin) === vin);
        if (duplicateVin) {
          setFormError(t("work_order_intake.error.vehicle_duplicate_vin", { plate: duplicateVin.plate_number }));
          setVehicleMode("select");
          setWorkOrderForm((prev) => ({ ...prev, vehicle_id: duplicateVin.id }));
          return;
        }
      }
    } catch {
      // backend remains source of truth
    }

    setFormError(null);
    const createdVehicle = await createVehicleMutation.mutateAsync({
      client_id: workOrderForm.client_id,
      plate_number: plateNumber,
      make_model: makeModel,
      year: year ? Number(year) : null,
      vin
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
      setFormError(t("work_order_intake.error.required"));
      return;
    }

    setFormError(null);
    const created = await createWorkOrderMutation.mutateAsync({
      client_id: workOrderForm.client_id,
      vehicle_id: workOrderForm.vehicle_id,
      description: workOrderForm.description.trim(),
      diagnosis: workOrderForm.diagnosis.trim() || null,
      mileage: workOrderForm.mileage ? Number(workOrderForm.mileage) : null,
      due_at: workOrderForm.due_at ? new Date(workOrderForm.due_at).toISOString() : null,
      estimated_amount: workOrderForm.estimated_amount ? Number(workOrderForm.estimated_amount) : null,
      intake_notes: workOrderForm.intake_notes.trim() || null,
      attachments: photos,
      assigned_employee_id: workOrderForm.assigned_employee_id || null,
      status: "new"
    });

    window.sessionStorage.removeItem("autoservice:intake-draft");
    router.push(ROUTES.workOrderDetail(created.id) as Route);
  };

  const isBusy = createClientMutation.isPending || createVehicleMutation.isPending || createWorkOrderMutation.isPending;
  const isVehicleStepActive = Boolean(workOrderForm.client_id);
  const isWorkOrderStepActive = Boolean(workOrderForm.vehicle_id);
  const canSubmitWorkOrder =
    Boolean(workOrderForm.client_id) &&
    Boolean(workOrderForm.vehicle_id) &&
    Boolean(workOrderForm.description.trim()) &&
    !isBusy;

  return (
    <PageLayout
      title={t("work_order_intake.title")}
      subtitle={t("work_order_intake.subtitle")}
      className="space-y-2"
      actions={
        <Button type="button" size="sm" variant="secondary" onClick={() => router.push(ROUTES.workOrders as Route)}>
          {t("work_order_intake.back")}
        </Button>
      }
    >
      <form className="mx-auto w-full max-w-[960px] space-y-2 pb-14" onSubmit={(event) => void onSubmit(event)}>
        {draftRestored ? (
          <div className="flex items-center justify-between rounded-md border border-primary/30 bg-primary/5 px-3 py-2 text-sm">
            <span>{t("work_order_intake.draft_restored")}</span>
            <Button type="button" size="sm" variant="ghost" onClick={() => { setWorkOrderForm(defaultWorkOrderForm()); window.sessionStorage.removeItem("autoservice:intake-draft"); setDraftRestored(false); }}>
              {t("work_order_intake.clear_draft")}
            </Button>
          </div>
        ) : null}
        <section className="space-y-1.5 border-b border-neutral-200 pb-3">
          <div className="flex flex-wrap items-center justify-between gap-1.5">
            <p className="flex items-center gap-1.5 text-sm font-semibold text-neutral-900">
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-neutral-300 text-[11px] font-semibold text-neutral-700">
                1
              </span>
              {t("common.client")}
            </p>
          </div>

          {clientMode === "select" ? (
            <div className="grid grid-cols-1 gap-1.5">
              <FormField id="client_id" label={t("common.client")} required>
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
                  placeholder={t("work_order_intake.select_client")}
                  searchPlaceholder={t("work_order_intake.search_client")}
                  emptyText={clientsLookupQuery.isLoading ? t("work_order_intake.loading_clients") : t("work_order_intake.no_clients")}
                  minSearchChars={2}
                  onSearchChange={setClientSearch}
                  serverSearch
                  minSearchText={t("work_order_intake.type_min_chars", { count: 2 })}
                  actionLabel={t("work_order_intake.create_client")}
                  onAction={() => {
                    setClientMode("create");
                    setFormError(null);
                  }}
                />
              </FormField>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex justify-end">
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="h-7 px-2 text-xs text-neutral-600"
                  onClick={() => {
                    setClientMode("select");
                    setFormError(null);
                  }}
                >
                  {t("work_order_intake.use_existing_client")}
                </Button>
              </div>
              <div className="grid grid-cols-1 gap-1.5 md:grid-cols-2">
                <FormField id="new-client-name" label={t("work_order_intake.client_name")} required>
                  <Input
                    fullHeight="sm"
                    id="new-client-name"
                    value={newClientForm.name}
                    onChange={(event) => setNewClientForm((prev) => ({ ...prev, name: event.target.value }))}
                  />
                </FormField>
                <FormField id="new-client-phone" label={t("common.phone")} required>
                  <PhoneInput
                    fullHeight="sm"
                    id="new-client-phone"
                    value={newClientForm.phone}
                    onChange={(value) => setNewClientForm((prev) => ({ ...prev, phone: value }))}
                  />
                </FormField>
                <FormField id="new-client-email" label={t("common.email")}>
                  <Input
                    fullHeight="sm"
                    id="new-client-email"
                    type="email"
                    value={newClientForm.email}
                    onChange={(event) => setNewClientForm((prev) => ({ ...prev, email: event.target.value }))}
                  />
                </FormField>
              </div>
              <div className="flex justify-end pt-0.5">
                <Button type="button" size="sm" variant="secondary" loading={createClientMutation.isPending} onClick={() => void onCreateClientInline()}>
                  {t("work_order_intake.create_client_continue")}
                </Button>
              </div>
            </div>
          )}
        </section>

        <section
          ref={vehicleSectionRef}
          className={cn("space-y-1.5 border-b border-neutral-200 pb-3 transition-opacity", !isVehicleStepActive && "opacity-50")}
        >
          <div className="flex flex-wrap items-center justify-between gap-1.5">
            <p className="flex items-center gap-1.5 text-sm font-semibold text-neutral-900">
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-neutral-300 text-[11px] font-semibold text-neutral-700">
                2
              </span>
              {t("common.vehicle")}
            </p>
          </div>

          {!isVehicleStepActive ? (
            <p className="text-xs text-neutral-600">{t("work_order_intake.complete_step_1")}</p>
          ) : vehicleMode === "select" ? (
            <div className="grid grid-cols-1 gap-1.5">
              <FormField id="vehicle_id" label={t("common.vehicle")} required>
                <Combobox
                  id="vehicle_id"
                  size="sm"
                  value={workOrderForm.vehicle_id}
                  onChange={(value) => setWorkOrderForm((prev) => ({ ...prev, vehicle_id: value }))}
                  options={vehicleOptions}
                  placeholder={t("work_order_intake.select_vehicle")}
                  searchPlaceholder={t("work_order_intake.search_vehicle")}
                  emptyText={vehiclesByClientQuery.isLoading ? t("work_order_intake.loading_vehicles") : t("work_order_intake.no_vehicles")}
                  actionLabel={t("work_order_intake.create_vehicle")}
                  onAction={() => {
                    setVehicleMode("create");
                    setFormError(null);
                  }}
                />
              </FormField>
            </div>
          ) : (
            <div className="space-y-1.5">
              <div className="flex justify-end">
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="h-7 px-2 text-xs text-neutral-600"
                  onClick={() => {
                    setVehicleMode("select");
                    setFormError(null);
                  }}
                >
                  {t("work_order_intake.use_existing_vehicle")}
                </Button>
              </div>
              <div className="grid grid-cols-1 gap-1.5 md:grid-cols-2">
                <FormField id="new-vehicle-plate" label={t("common.plate_number")} required>
                  <Input
                    fullHeight="sm"
                    id="new-vehicle-plate"
                    value={newVehicleForm.plate_number}
                    onChange={(event) => setNewVehicleForm((prev) => ({ ...prev, plate_number: event.target.value }))}
                  />
                </FormField>
                <FormField id="new-vehicle-model" label={t("common.make_model")} required>
                  <Input
                    fullHeight="sm"
                    id="new-vehicle-model"
                    value={newVehicleForm.make_model}
                    onChange={(event) => setNewVehicleForm((prev) => ({ ...prev, make_model: event.target.value }))}
                  />
                </FormField>
                <FormField id="new-vehicle-year" label={t("common.year")}>
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
              <div className="flex justify-end pt-0.5">
                <Button type="button" size="sm" variant="secondary" loading={createVehicleMutation.isPending} onClick={() => void onCreateVehicleInline()}>
                  {t("work_order_intake.create_vehicle_continue")}
                </Button>
              </div>
            </div>
          )}
        </section>

        <section
          ref={workOrderSectionRef}
          className={cn("grid grid-cols-1 gap-1.5 pb-3 transition-opacity md:grid-cols-2", !isWorkOrderStepActive && "opacity-50")}
        >
          <p className="flex items-center gap-1.5 text-sm font-semibold text-neutral-900 md:col-span-2">
            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-neutral-300 text-[11px] font-semibold text-neutral-700">
              3
            </span>
            {t("common.work_order")}
          </p>

          {!isWorkOrderStepActive ? (
            <p className="text-xs text-neutral-600 md:col-span-2">{t("work_order_intake.complete_step_2")}</p>
          ) : (
            <>
              <FormField id="assigned_employee_id" label={t("work_order_intake.assignee_optional")} className="md:col-span-2">
                <Select
                  className="h-8"
                  id="assigned_employee_id"
                  value={workOrderForm.assigned_employee_id}
                  onChange={(event) => setWorkOrderForm((prev) => ({ ...prev, assigned_employee_id: event.target.value }))}
                >
                  <option value="">{t("work_orders.unassigned")}</option>
                  {(employeesQuery.data?.items ?? []).map((employee) => (
                    <option key={employee.employee_id} value={employee.employee_id}>
                      {(employee.full_name?.trim() || employee.email).replace(/[,\s]+$/g, "")} (
                      {employeeRoleLabel(employee.role, t)})
                    </option>
                  ))}
                </Select>
              </FormField>

              <FormField id="description" label={t("work_order_intake.description_label")} required className="md:col-span-2">
                <Textarea
                  className="min-h-20"
                  id="description"
                  value={workOrderForm.description}
                  onChange={(event) => setWorkOrderForm((prev) => ({ ...prev, description: event.target.value }))}
                />
              </FormField>
              <FormField id="diagnosis" label={t("work_order_intake.diagnosis")} className="md:col-span-2">
                <Textarea id="diagnosis" value={workOrderForm.diagnosis} onChange={(event) => setWorkOrderForm((prev) => ({ ...prev, diagnosis: event.target.value }))} />
              </FormField>
              <FormField id="mileage" label={t("work_order_intake.mileage")}>
                <Input id="mileage" type="number" min="0" inputMode="numeric" value={workOrderForm.mileage} onChange={(event) => setWorkOrderForm((prev) => ({ ...prev, mileage: event.target.value }))} />
              </FormField>
              <FormField id="due_at" label={t("work_order_intake.due_at")}>
                <Input id="due_at" type="datetime-local" value={workOrderForm.due_at} onChange={(event) => setWorkOrderForm((prev) => ({ ...prev, due_at: event.target.value }))} />
              </FormField>
              <FormField id="estimated_amount" label={t("work_order_intake.estimated_amount")}>
                <Input id="estimated_amount" type="number" min="0" step="0.01" inputMode="decimal" value={workOrderForm.estimated_amount} onChange={(event) => setWorkOrderForm((prev) => ({ ...prev, estimated_amount: event.target.value }))} />
              </FormField>
              <FormField id="intake_notes" label={t("work_order_intake.intake_notes")}>
                <Textarea id="intake_notes" value={workOrderForm.intake_notes} onChange={(event) => setWorkOrderForm((prev) => ({ ...prev, intake_notes: event.target.value }))} />
              </FormField>
              <FormField id="intake-photos" label={t("work_order_intake.photos")} className="md:col-span-2">
                <Input
                  id="intake-photos"
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  multiple
                  onChange={(event) => {
                    const files = Array.from(event.target.files ?? []);
                    if (photos.length + files.length > 5 || files.some((file) => file.size > 500_000)) {
                      setFormError(t("work_order_intake.photos_error"));
                      event.target.value = "";
                      return;
                    }
                    void Promise.all(files.map((file) => new Promise<IntakePhoto>((resolve, reject) => {
                      const reader = new FileReader();
                      reader.onload = () => resolve({ name: file.name, content_type: file.type as IntakePhoto["content_type"], data_url: String(reader.result) });
                      reader.onerror = reject;
                      reader.readAsDataURL(file);
                    }))).then((items) => { setPhotos((current) => [...current, ...items]); setFormError(null); }).catch(() => setFormError(t("work_order_intake.photos_error")));
                  }}
                />
                {photos.length ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {photos.map((photo, index) => (
                      <div key={`${photo.name}-${index}`} className="relative h-20 w-20 overflow-hidden rounded-md border border-neutral-200">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={photo.data_url} alt={photo.name} className="h-full w-full object-cover" />
                        <button type="button" aria-label={t("common.remove")} className="absolute right-1 top-1 rounded bg-neutral-900/70 px-1 text-xs text-white" onClick={() => setPhotos((current) => current.filter((_, itemIndex) => itemIndex !== index))}>×</button>
                      </div>
                    ))}
                  </div>
                ) : null}
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

        <div className="sticky bottom-0 z-10 -mx-1 mt-1 bg-gradient-to-t from-neutral-100/95 via-neutral-100/92 to-transparent px-1 pt-3 pb-[max(8px,env(safe-area-inset-bottom))]">
          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-neutral-200 py-2">
            <Button type="button" size="sm" variant="secondary" onClick={() => router.push(ROUTES.workOrders as Route)}>
              {t("common.cancel")}
            </Button>
            <Button
              type="submit"
              size="sm"
              variant="primary"
              loading={createWorkOrderMutation.isPending}
              disabled={!canSubmitWorkOrder}
            >
              {t("work_order_intake.submit")}
            </Button>
          </div>
        </div>
      </form>
    </PageLayout>
  );
}
