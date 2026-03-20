"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import { formatPhoneInput, normalizePhoneForSubmit } from "@/core/lib/phone";
import { Button, Card, FormActions, FormField, Input, PhoneInput, Textarea } from "@/design-system/primitives";
import { PageLayout, Section, StateBoundary } from "@/design-system/patterns";
import {
  fetchClient,
  fetchVehiclesByClient,
  mvpQueryKeys,
  updateClient
} from "@/features/workspace/api/mvp-api";

export function ClientDetailScreen({ clientId }: { clientId: string }): JSX.Element {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    phone: "",
    email: "",
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

  const updateMutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateClient>[1]) => updateClient(clientId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.client(clientId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.vehiclesByClient(clientId) });
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
      comment: clientQuery.data.comment ?? ""
    });
  }, [clientQuery.data]);

  return (
    <PageLayout title="Client detail" subtitle={clientId}>
      <StateBoundary loading={clientQuery.isLoading} error={clientQuery.error?.message}>
        {clientQuery.data ? (
          <>
            <Section
              title={clientQuery.data.name}
              description={`Created ${new Date(clientQuery.data.created_at).toLocaleString()}`}
              actions={
                <Link href={ROUTES.clients}>
                  <Button variant="secondary">Back to clients</Button>
                </Link>
              }
            >
              <form
                className="grid grid-cols-1 gap-2 md:grid-cols-2"
                onSubmit={(event) => {
                  event.preventDefault();
                  void updateMutation.mutateAsync({
                    name: form.name.trim(),
                    phone: normalizePhoneForSubmit(form.phone),
                    email: form.email.trim() || null,
                    comment: form.comment.trim() || null,
                    version: clientQuery.data!.version
                  });
                }}
              >
                <FormField id="name" label="Name" required>
                  <Input id="name" value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} />
                </FormField>
                <FormField id="phone" label="Phone" required>
                  <PhoneInput id="phone" value={form.phone} onChange={(phone) => setForm((prev) => ({ ...prev, phone }))} />
                </FormField>
                <FormField id="email" label="Email">
                  <Input id="email" value={form.email} onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))} />
                </FormField>
                <div className="md:col-span-2">
                  <FormField id="comment" label="Comment">
                    <Textarea id="comment" value={form.comment} onChange={(event) => setForm((prev) => ({ ...prev, comment: event.target.value }))} />
                  </FormField>
                </div>
                {updateMutation.error ? <p className="text-sm text-error md:col-span-2">{updateMutation.error.message}</p> : null}
                <div className="md:col-span-2">
                  <FormActions>
                    <Button type="submit" loading={updateMutation.isPending}>
                      Save changes
                    </Button>
                  </FormActions>
                </div>
              </form>
            </Section>

            <Section title="Vehicles" description="Vehicles linked to this client">
              {vehiclesQuery.isLoading ? (
                <p className="text-sm text-neutral-600">Loading vehicles...</p>
              ) : vehiclesQuery.error ? (
                <p className="text-sm text-error">{vehiclesQuery.error.message}</p>
              ) : vehiclesQuery.data?.length ? (
                <div className="space-y-1">
                  {vehiclesQuery.data.map((vehicle) => (
                    <Card key={vehicle.id} className="border-neutral-200 p-2">
                      <div className="flex flex-wrap items-center justify-between gap-1">
                        <div>
                          <p className="text-sm font-medium text-neutral-900">{vehicle.plate_number}</p>
                          <p className="text-sm text-neutral-600">{vehicle.make_model}</p>
                        </div>
                        <Link href={ROUTES.vehicleDetail(vehicle.id) as Route}>
                          <Button variant="secondary" size="sm">
                            Open vehicle
                          </Button>
                        </Link>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-neutral-600">No vehicles linked yet.</p>
              )}
            </Section>
          </>
        ) : null}
      </StateBoundary>
    </PageLayout>
  );
}
