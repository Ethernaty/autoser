"use client";

import Link from "next/link";
import type { Route } from "next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import { Badge, Button, Card, FormActions, FormField, Input, Textarea } from "@/design-system/primitives";
import { PageLayout, Section, StateBoundary } from "@/design-system/patterns";
import {
  fetchClient,
  fetchVehicle,
  fetchVehicleWorkOrders,
  mvpQueryKeys,
  updateVehicle
} from "@/features/workspace/api/mvp-api";

function formatMoney(value: string): string {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return value;
  }
  return parsed.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function VehicleDetailScreen({ vehicleId }: { vehicleId: string }): JSX.Element {
  const queryClient = useQueryClient();

  const vehicleQuery = useQuery({
    queryKey: mvpQueryKeys.vehicle(vehicleId),
    queryFn: () => fetchVehicle(vehicleId)
  });

  const clientQuery = useQuery({
    queryKey: mvpQueryKeys.client(vehicleQuery.data?.client_id ?? ""),
    queryFn: () => fetchClient(vehicleQuery.data!.client_id),
    enabled: Boolean(vehicleQuery.data?.client_id)
  });

  const historyQuery = useQuery({
    queryKey: mvpQueryKeys.vehicleWorkOrders(vehicleId),
    queryFn: () => fetchVehicleWorkOrders(vehicleId)
  });

  const updateMutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateVehicle>[1]) => updateVehicle(vehicleId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.vehicle(vehicleId) });
      void queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    }
  });

  return (
    <PageLayout title="Vehicle detail" subtitle={vehicleId}>
      <StateBoundary loading={vehicleQuery.isLoading} error={vehicleQuery.error?.message}>
        {vehicleQuery.data ? (
          <>
            <Section
              title={`${vehicleQuery.data.plate_number} • ${vehicleQuery.data.make_model}`}
              description={`Created ${new Date(vehicleQuery.data.created_at).toLocaleString()}`}
              actions={
                <div className="flex items-center gap-1">
                  {clientQuery.data ? (
                    <Link href={ROUTES.clientDetail(clientQuery.data.id) as Route}>
                      <Button variant="secondary">Client</Button>
                    </Link>
                  ) : null}
                  <Link href={ROUTES.vehicles}>
                    <Button variant="secondary">Back</Button>
                  </Link>
                </div>
              }
            >
              <form
                className="grid grid-cols-1 gap-2 md:grid-cols-2"
                onSubmit={(event) => {
                  event.preventDefault();
                  const formData = new FormData(event.currentTarget);
                  void updateMutation.mutateAsync({
                    plate_number: String(formData.get("plate_number") ?? "").trim(),
                    make_model: String(formData.get("make_model") ?? "").trim(),
                    year: String(formData.get("year") ?? "").trim()
                      ? Number(formData.get("year"))
                      : null,
                    vin: String(formData.get("vin") ?? "").trim() || null,
                    comment: String(formData.get("comment") ?? "").trim() || null
                  });
                }}
              >
                <FormField id="plate_number" label="Plate number" required>
                  <Input id="plate_number" name="plate_number" defaultValue={vehicleQuery.data.plate_number} />
                </FormField>
                <FormField id="make_model" label="Make/model" required>
                  <Input id="make_model" name="make_model" defaultValue={vehicleQuery.data.make_model} />
                </FormField>
                <FormField id="year" label="Year">
                  <Input id="year" name="year" defaultValue={vehicleQuery.data.year ?? ""} />
                </FormField>
                <FormField id="vin" label="VIN">
                  <Input id="vin" name="vin" defaultValue={vehicleQuery.data.vin ?? ""} />
                </FormField>
                <div className="md:col-span-2">
                  <FormField id="comment" label="Comment">
                    <Textarea id="comment" name="comment" defaultValue={vehicleQuery.data.comment ?? ""} />
                  </FormField>
                </div>
                {updateMutation.error ? <p className="text-sm text-error md:col-span-2">{updateMutation.error.message}</p> : null}
                <div className="md:col-span-2">
                  <FormActions>
                    <Button type="submit" loading={updateMutation.isPending}>
                      Save
                    </Button>
                  </FormActions>
                </div>
              </form>
            </Section>

            <Section title="Work-order history" description="Orders linked to this vehicle">
              {historyQuery.isLoading ? (
                <p className="text-sm text-neutral-600">Loading history...</p>
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
                          <p className="text-xs text-neutral-600">
                            Created {new Date(item.created_at).toLocaleString()}
                          </p>
                        </div>
                        <div className="text-right">
                          <Badge tone="neutral">{item.status}</Badge>
                          <p className="text-xs text-neutral-700">Total: {formatMoney(item.total_amount)}</p>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-neutral-600">No work orders linked yet.</p>
              )}
            </Section>
          </>
        ) : null}
      </StateBoundary>
    </PageLayout>
  );
}
