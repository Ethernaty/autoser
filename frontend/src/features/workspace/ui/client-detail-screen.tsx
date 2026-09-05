"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import { formatPhoneForDisplay, formatPhoneInput, normalizePhoneForSubmit } from "@/core/lib/phone";
import { Button, Card, FormActions, FormField, Input, PhoneInput, Textarea } from "@/design-system/primitives";
import { PageLayout, Section, StateBoundary } from "@/design-system/patterns";
import {
  fetchClient,
  fetchClientWorkOrders,
  fetchVehiclesByClient,
  mvpQueryKeys,
  updateClient
} from "@/features/workspace/api/mvp-api";
import { OrderStatusBadge } from "@/features/workspace/ui/order-status-badge";
import { useI18n } from "@/shared/i18n";

function formatMoney(value: string): string {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return value;
  }
  return parsed.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function ClientDetailScreen({ clientId }: { clientId: string }): JSX.Element {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    phone: "",
    email: "",
    source: "",
    comment: ""
  });

  const clientQuery = useQuery({
    queryKey: mvpQueryKeys.client(clientId),
    queryFn: () => fetchClient(clientId)
  });

  const vehiclesQuery = useQuery({
    queryKey: mvpQueryKeys.vehiclesByClient(clientId),
    queryFn: () => fetchVehiclesByClient(clientId)
  });

  const historyQuery = useQuery({
    queryKey: mvpQueryKeys.clientWorkOrders(clientId, 50, 0),
    queryFn: () => fetchClientWorkOrders(clientId, { limit: 50, offset: 0 })
  });

  const updateMutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateClient>[1]) => updateClient(clientId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.client(clientId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.vehiclesByClient(clientId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.clientWorkOrders(clientId, 50, 0) });
      void queryClient.invalidateQueries({ queryKey: ["clients"] });
    }
  });

  useEffect(() => {
    if (!clientQuery.data) {
      return;
    }
    setForm({
      name: clientQuery.data.name,
      phone: formatPhoneInput(clientQuery.data.phone),
      email: clientQuery.data.email ?? "",
      source: clientQuery.data.source ?? "",
      comment: clientQuery.data.comment ?? ""
    });
  }, [clientQuery.data]);

  return (
    <PageLayout title={t("client_detail.title")}> 
      <StateBoundary loading={clientQuery.isLoading} error={clientQuery.error?.message}>
        {clientQuery.data ? (
          <>
            <Section
              title={clientQuery.data.name}
              description={`${t("work_orders.created")} ${new Date(clientQuery.data.created_at).toLocaleString()}`}
              actions={
                <div className="flex flex-wrap gap-2">
                  <Link href={`${ROUTES.workOrderNew}?client_id=${clientId}` as Route}><Button>{t("work_orders.new")}</Button></Link>
                  <Link href={`${ROUTES.vehicles}?create=1&client_id=${clientId}` as Route}><Button variant="secondary">{t("vehicles.add")}</Button></Link>
                  <Link href={ROUTES.clients}><Button variant="secondary">{t("clients.back")}</Button></Link>
                </div>
              }
            >
              <div className="grid grid-cols-1 gap-2 lg:grid-cols-[320px_1fr]">
                <Card className="space-y-2 border-neutral-200 p-2">
                  <h3 className="text-sm font-semibold text-neutral-900">{t("client_detail.contact_profile")}</h3>
                  <div className="space-y-1 text-sm text-neutral-700">
                    <p>
                      <span className="text-neutral-500">{t("common.phone")}:</span>{" "}
                      <a className="text-primary hover:underline" href={`tel:${clientQuery.data.phone}`}>{formatPhoneForDisplay(clientQuery.data.phone)}</a>
                    </p>
                    <p>
                      <span className="text-neutral-500">{t("common.email")}:</span> {clientQuery.data.email ?? t("common.not_provided")}
                    </p>
                    <p>
                      <span className="text-neutral-500">{t("clients.form.source")}:</span> {clientQuery.data.source ?? t("common.not_provided")}
                    </p>
                    <p>
                      <span className="text-neutral-500">{t("common.vehicles")}:</span> {clientQuery.data.vehicle_count ?? 0}
                    </p>
                    <p>
                      <span className="text-neutral-500">{t("client_detail.visits")}:</span> {clientQuery.data.work_order_count ?? 0}
                    </p>
                  </div>
                </Card>

                <form
                  className="grid grid-cols-1 gap-2 md:grid-cols-2"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void updateMutation.mutateAsync({
                      name: form.name.trim(),
                      phone: normalizePhoneForSubmit(form.phone),
                      email: form.email.trim() || null,
                      source: form.source.trim() || null,
                      comment: form.comment.trim() || null,
                      version: clientQuery.data!.version
                    });
                  }}
                >
                  <FormField id="name" label={t("clients.form.full_name")} required>
                    <Input id="name" value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} />
                  </FormField>
                  <FormField id="phone" label={t("common.phone")} required>
                    <PhoneInput id="phone" value={form.phone} onChange={(phone) => setForm((prev) => ({ ...prev, phone }))} />
                  </FormField>
                  <FormField id="email" label={t("common.email")}>
                    <Input id="email" value={form.email} onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))} />
                  </FormField>
                  <FormField id="source" label={t("clients.form.source")}>
                    <Input id="source" value={form.source} onChange={(event) => setForm((prev) => ({ ...prev, source: event.target.value }))} />
                  </FormField>
                  <div className="md:col-span-2">
                    <FormField id="comment" label={t("common.comment")}>
                      <Textarea id="comment" value={form.comment} onChange={(event) => setForm((prev) => ({ ...prev, comment: event.target.value }))} />
                    </FormField>
                  </div>
                  {updateMutation.error ? <p className="text-sm text-error md:col-span-2">{updateMutation.error.message}</p> : null}
                  <div className="md:col-span-2">
                    <FormActions>
                      <Button type="submit" loading={updateMutation.isPending}>
                        {t("common.save")}
                      </Button>
                    </FormActions>
                  </div>
                </form>
              </div>
            </Section>

            <Section title={t("client_detail.vehicles.title")} description={t("client_detail.vehicles.description")}>
              {vehiclesQuery.isLoading ? (
                <p className="text-sm text-neutral-600">{t("client_detail.loading_vehicles")}</p>
              ) : vehiclesQuery.error ? (
                <p className="text-sm text-error">{vehiclesQuery.error.message}</p>
              ) : vehiclesQuery.data?.length ? (
                <div className="space-y-1">
                  {vehiclesQuery.data.map((vehicle) => (
                    <Card key={vehicle.id} className="border-neutral-200 p-2">
                      <div className="flex flex-wrap items-center justify-between gap-1">
                        <div>
                          <p className="text-sm font-medium text-neutral-900">{vehicle.plate_number}</p>
                          <p className="text-sm text-neutral-600">
                            {vehicle.make_model}
                            {vehicle.year ? ` | ${vehicle.year}` : ""}
                          </p>
                        </div>
                        <Link href={ROUTES.vehicleDetail(vehicle.id) as Route}>
                          <Button variant="secondary" size="sm">
                            {t("common.open")}
                          </Button>
                        </Link>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-neutral-600">{t("client_detail.vehicles.empty")}</p>
              )}
            </Section>

            <Section title={t("client_detail.history.title")} description={t("client_detail.history.description")}>
              {historyQuery.isLoading ? (
                <p className="text-sm text-neutral-600">{t("client_detail.loading_history")}</p>
              ) : historyQuery.error ? (
                <p className="text-sm text-error">{historyQuery.error.message}</p>
              ) : historyQuery.data?.length ? (
                <div className="space-y-1">
                  {historyQuery.data.map((visit) => (
                    <Card key={visit.id} className="border-neutral-200 p-2">
                      <div className="flex flex-wrap items-start justify-between gap-1">
                        <div>
                          <Link href={ROUTES.workOrderDetail(visit.id) as Route} className="text-sm font-medium text-primary hover:underline">
                            {visit.description}
                          </Link>
                          <p className="text-xs text-neutral-600">{t("client_detail.visit_date")}: {new Date(visit.visit_at).toLocaleString()}</p>
                          {visit.vehicle_id ? (
                            <p className="text-xs text-neutral-600">
                              {t("common.vehicle")}: {visit.vehicle_plate_number ?? t("common.unknown")}
                              {visit.vehicle_make_model ? ` | ${visit.vehicle_make_model}` : ""}
                            </p>
                          ) : null}
                          <p className="text-xs text-neutral-600">{t("client_detail.work_summary")}: {visit.work_summary ?? t("client_detail.no_line_items")}</p>
                        </div>
                        <div className="min-w-[180px] text-right">
                          <OrderStatusBadge status={visit.status} />
                          <p className="text-xs text-neutral-700">{t("work_orders.kpi.total")}: {formatMoney(visit.total_amount)}</p>
                          <p className="text-xs text-neutral-600">
                            {t("work_orders.kpi.paid")}: {formatMoney(visit.paid_amount)} | {t("work_orders.kpi.remaining")}: {formatMoney(visit.remaining_amount)}
                          </p>
                          <Link href={ROUTES.workOrderDetail(visit.id) as Route}>
                            <Button variant="secondary" size="sm" className="mt-1">{t("common.open")}</Button>
                          </Link>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-neutral-600">{t("client_detail.history.empty")}</p>
              )}
            </Section>
          </>
        ) : null}
      </StateBoundary>
    </PageLayout>
  );
}
