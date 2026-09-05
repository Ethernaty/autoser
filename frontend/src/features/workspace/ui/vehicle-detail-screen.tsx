"use client";

import Link from "next/link";
import type { Route } from "next";
import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import { Badge, Button, Card, FormActions, FormField, Input, Textarea } from "@/design-system/primitives";
import { PageLayout, Section, StateBoundary } from "@/design-system/patterns";
import {
  fetchClient,
  fetchVehicle,
  fetchVehicleHistory,
  mvpQueryKeys,
  updateVehicle
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

export function VehicleDetailScreen({ vehicleId }: { vehicleId: string }): JSX.Element {
  const { t } = useI18n();
  const queryClient = useQueryClient();

  const vehicleQuery = useQuery({
    queryKey: mvpQueryKeys.vehicle(vehicleId),
    queryFn: () => fetchVehicle(vehicleId)
  });

  const currentOwnerQuery = useQuery({
    queryKey: mvpQueryKeys.client(vehicleQuery.data?.client_id ?? ""),
    queryFn: () => fetchClient(vehicleQuery.data!.client_id),
    enabled: Boolean(vehicleQuery.data?.client_id)
  });

  const historyQuery = useQuery({
    queryKey: mvpQueryKeys.vehicleHistory(vehicleId, 100, 0),
    queryFn: () => fetchVehicleHistory(vehicleId, { limit: 100, offset: 0 })
  });

  const updateMutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateVehicle>[1]) => updateVehicle(vehicleId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.vehicle(vehicleId) });
      void queryClient.invalidateQueries({ queryKey: ["vehicles"] });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.vehicleHistory(vehicleId, 100, 0) });
    }
  });

  const owners = useMemo(() => {
    const map = new Map<string, string>();
    if (currentOwnerQuery.data) {
      map.set(currentOwnerQuery.data.id, currentOwnerQuery.data.name);
    }
    for (const item of historyQuery.data ?? []) {
      if (item.client_id && item.client_name) {
        map.set(item.client_id, item.client_name);
      }
    }
    return Array.from(map.entries()).map(([id, name]) => ({ id, name }));
  }, [currentOwnerQuery.data, historyQuery.data]);

  return (
    <PageLayout title={t("vehicle_detail.title")}>
      <StateBoundary loading={vehicleQuery.isLoading} error={vehicleQuery.error?.message}>
        {vehicleQuery.data ? (
          <>
            <Section
              title={`${vehicleQuery.data.plate_number} | ${vehicleQuery.data.make_model}`}
              description={`${t("work_orders.created")} ${new Date(vehicleQuery.data.created_at).toLocaleString()}`}
              actions={
                <div className="flex items-center gap-1">
                  <Link href={`${ROUTES.workOrderNew}?client_id=${vehicleQuery.data.client_id}&vehicle_id=${vehicleId}` as Route}>
                    <Button>{t("work_orders.new")}</Button>
                  </Link>
                  {currentOwnerQuery.data ? (
                    <Link href={ROUTES.clientDetail(currentOwnerQuery.data.id) as Route}>
                      <Button variant="secondary">{t("vehicle_detail.current_owner")}</Button>
                    </Link>
                  ) : null}
                  <Link href={ROUTES.vehicles}>
                    <Button variant="secondary">{t("vehicles.back")}</Button>
                  </Link>
                </div>
              }
            >
              <div className="grid grid-cols-1 gap-2 lg:grid-cols-[320px_1fr]">
                <Card className="space-y-2 border-neutral-200 p-2">
                  <h3 className="text-sm font-semibold text-neutral-900">{t("vehicle_detail.context")}</h3>
                  <div className="space-y-1 text-sm text-neutral-700">
                    <p>
                      <span className="text-neutral-500">{t("common.plate_number")}:</span> {vehicleQuery.data.plate_number}
                    </p>
                    <p>
                      <span className="text-neutral-500">{t("common.make_model")}:</span> {vehicleQuery.data.make_model}
                    </p>
                    <p>
                      <span className="text-neutral-500">{t("common.year")}:</span> {vehicleQuery.data.year ?? t("common.not_set")}
                    </p>
                    <p>
                      <span className="text-neutral-500">{t("common.vin")}:</span> {vehicleQuery.data.vin ?? t("common.not_set")}
                    </p>
                    <p>
                      <span className="text-neutral-500">{t("client_detail.visits")}:</span> {vehicleQuery.data.work_order_count ?? 0}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{t("vehicle_detail.owners_history")}</p>
                    {owners.length ? (
                      <div className="flex flex-wrap gap-1">
                        {owners.map((owner) => (
                          <Link key={owner.id} href={ROUTES.clientDetail(owner.id) as Route}>
                            <Badge tone="neutral">{owner.name}</Badge>
                          </Link>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-neutral-500">{t("vehicle_detail.no_owner_history")}</p>
                    )}
                  </div>
                </Card>

                <form
                  className="grid grid-cols-1 gap-2 md:grid-cols-2"
                  onSubmit={(event) => {
                    event.preventDefault();
                    const formData = new FormData(event.currentTarget);
                    void updateMutation.mutateAsync({
                      plate_number: String(formData.get("plate_number") ?? "").trim(),
                      make_model: String(formData.get("make_model") ?? "").trim(),
                      year: String(formData.get("year") ?? "").trim() ? Number(formData.get("year")) : null,
                      vin: String(formData.get("vin") ?? "").trim() || null,
                      comment: String(formData.get("comment") ?? "").trim() || null
                    });
                  }}
                >
                  <FormField id="plate_number" label={t("common.plate_number")} required>
                    <Input id="plate_number" name="plate_number" defaultValue={vehicleQuery.data.plate_number} />
                  </FormField>
                  <FormField id="make_model" label={t("common.make_model")} required>
                    <Input id="make_model" name="make_model" defaultValue={vehicleQuery.data.make_model} />
                  </FormField>
                  <FormField id="year" label={t("common.year")}>
                    <Input id="year" name="year" defaultValue={vehicleQuery.data.year ?? ""} />
                  </FormField>
                  <FormField id="vin" label={t("common.vin")}>
                    <Input id="vin" name="vin" defaultValue={vehicleQuery.data.vin ?? ""} />
                  </FormField>
                  <div className="md:col-span-2">
                    <FormField id="comment" label={t("common.comment")}>
                      <Textarea id="comment" name="comment" defaultValue={vehicleQuery.data.comment ?? ""} />
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

            <Section title={t("vehicle_detail.history.title")} description={t("vehicle_detail.history.description")}>
              {historyQuery.isLoading ? (
                <p className="text-sm text-neutral-600">{t("vehicle_detail.loading_history")}</p>
              ) : historyQuery.error ? (
                <p className="text-sm text-error">{historyQuery.error.message}</p>
              ) : historyQuery.data?.length ? (
                <div className="space-y-1">
                  {historyQuery.data.map((item) => (
                    <Card key={item.id} className="border-neutral-200 p-2">
                      <div className="flex flex-wrap items-start justify-between gap-1">
                        <div>
                          <Link href={ROUTES.workOrderDetail(item.id) as Route} className="text-sm font-medium text-primary hover:underline">
                            {item.description}
                          </Link>
                          <p className="text-xs text-neutral-600">{t("client_detail.visit_date")}: {new Date(item.visit_at).toLocaleString()}</p>
                          <p className="text-xs text-neutral-600">{t("vehicle_detail.owner_at_visit")}: {item.client_name ?? t("common.unknown")}</p>
                          <p className="text-xs text-neutral-600">{t("client_detail.work_summary")}: {item.work_summary ?? t("client_detail.no_line_items")}</p>
                        </div>
                        <div className="min-w-[180px] text-right">
                          <OrderStatusBadge status={item.status} />
                          <p className="text-xs text-neutral-700">{t("work_orders.kpi.total")}: {formatMoney(item.total_amount)}</p>
                          <p className="text-xs text-neutral-600">
                            {t("work_orders.kpi.paid")}: {formatMoney(item.paid_amount)} | {t("work_orders.kpi.remaining")}: {formatMoney(item.remaining_amount)}
                          </p>
                          <Link href={ROUTES.workOrderDetail(item.id) as Route}>
                            <Button variant="secondary" size="sm" className="mt-1">
                              {t("common.open")}
                            </Button>
                          </Link>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-neutral-600">{t("vehicle_detail.history.empty")}</p>
              )}
            </Section>
          </>
        ) : null}
      </StateBoundary>
    </PageLayout>
  );
}
