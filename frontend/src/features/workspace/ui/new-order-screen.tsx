"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { formatPhoneForDisplay, formatPhoneInput, normalizePhoneForSubmit } from "@/core/lib/phone";
import { ROUTES } from "@/core/config/routes";
import { Button } from "@/design-system/primitives/button";
import { Card } from "@/design-system/primitives/card";
import { Input } from "@/design-system/primitives/input";
import { PhoneInput } from "@/design-system/primitives/phone-input";
import { PageLayout } from "@/design-system/patterns";
import { DisableIfNoAccess } from "@/features/access/ui/access-guard";
import { useWorkspaceClientSearchQuery, useCreateWorkflowOrderMutation } from "@/features/workspace/hooks";

export function NewOrderScreen(): JSX.Element {
  const router = useRouter();

  const [phone, setPhone] = useState("");
  const [clientName, setClientName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [selectedClientId, setSelectedClientId] = useState<string | undefined>(undefined);

  const createMutation = useCreateWorkflowOrderMutation();
  const lookupQuery = useMemo(() => phone.trim() || clientName.trim(), [phone, clientName]);
  const suggestionsQuery = useWorkspaceClientSearchQuery(lookupQuery);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();

    await createMutation.mutateAsync({
      phone: normalizePhoneForSubmit(phone),
      clientName,
      description,
      price: Number(price),
      selectedClientId
    });

    router.push(ROUTES.dashboard);
  };

  return (
    <PageLayout title="New order" subtitle="Fast order intake for front-desk flow">
      <Card className="space-y-3 p-3">
        <div className="space-y-1">
          <label className="text-sm font-medium text-neutral-700" htmlFor="lookup">
            Phone lookup
          </label>
          <PhoneInput
            id="lookup"
            value={phone}
            onChange={(nextPhone) => {
              setPhone(nextPhone);
              setSelectedClientId(undefined);
            }}
          />
        </div>

        {suggestionsQuery.data?.items?.length ? (
          <div className="space-y-1">
            <p className="text-sm font-medium text-neutral-700">Matches</p>
            <div className="grid grid-cols-1 gap-1 md:grid-cols-2">
              {suggestionsQuery.data.items.map((client) => (
                <button
                  key={client.id}
                  type="button"
                  className="flex min-h-6 items-center justify-between rounded-md border border-neutral-200 px-2 text-left"
                  onClick={() => {
                    setSelectedClientId(client.id);
                    setPhone(formatPhoneInput(client.phone));
                    setClientName(client.name);
                  }}
                  data-ui="interactive"
                >
                  <span className="text-sm text-neutral-900">{client.name}</span>
                  <span className="text-xs text-neutral-600">{formatPhoneForDisplay(client.phone)}</span>
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </Card>

      <Card className="p-3">
        <form className="space-y-2" onSubmit={onSubmit}>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            <div className="space-y-1">
              <label className="text-sm font-medium text-neutral-700" htmlFor="phone">
                Phone
              </label>
              <PhoneInput id="phone" required value={phone} onChange={setPhone} />
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-neutral-700" htmlFor="clientName">
                Client name (optional)
              </label>
              <Input id="clientName" value={clientName} onChange={(event) => setClientName(event.target.value)} />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-neutral-700" htmlFor="description">
              Work description
            </label>
            <textarea
              id="description"
              className="min-h-10 w-full rounded-md border border-neutral-300 bg-neutral-0 px-2 py-1 text-sm"
              required
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-neutral-700" htmlFor="price">
              Price
            </label>
            <Input id="price" required value={price} onChange={(event) => setPrice(event.target.value)} placeholder="1500.00" />
          </div>

          {createMutation.error ? <p className="text-sm font-medium text-danger">{createMutation.error.message}</p> : null}

          <div className="flex justify-end">
            <DisableIfNoAccess permission="orders.create" limitType="maxOrdersPerMonth">
              {(disabled, onUpgrade) => (
                <div className="flex items-center gap-1">
                  <Button type="submit" disabled={disabled} loading={createMutation.isPending}>
                    Create order
                  </Button>
                  {disabled ? (
                    <Button type="button" variant="quiet" onClick={onUpgrade}>
                      Upgrade
                    </Button>
                  ) : null}
                </div>
              )}
            </DisableIfNoAccess>
          </div>
        </form>
      </Card>
    </PageLayout>
  );
}
