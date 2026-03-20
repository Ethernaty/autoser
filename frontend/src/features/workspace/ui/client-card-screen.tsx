"use client";

import { useState } from "react";

import { formatPhoneForDisplay } from "@/core/lib/phone";
import { Button } from "@/design-system/primitives/button";
import { Card } from "@/design-system/primitives/card";
import { Input } from "@/design-system/primitives/input";
import { DetailLayout, PageLayout, StateBoundary } from "@/design-system/patterns";
import { useWorkspaceClientCardQuery } from "@/features/workspace/hooks";
import { OrderStatusBadge } from "@/features/workspace/ui/order-status-badge";

export function ClientCardScreen(): JSX.Element {
  const [query, setQuery] = useState("");
  const [activeQuery, setActiveQuery] = useState("");
  const [clientId, setClientId] = useState<string | undefined>(undefined);

  const clientCardQuery = useWorkspaceClientCardQuery({ q: activeQuery, clientId });

  return (
    <PageLayout title="Client card" subtitle="Find client and check order history">
      <Card className="p-3">
        <form
          className="flex flex-col gap-2 md:flex-row"
          onSubmit={(event) => {
            event.preventDefault();
            setActiveQuery(query.trim());
            setClientId(undefined);
          }}
        >
          <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Phone, name, email" />
          <Button type="submit" variant="secondary">
            Search
          </Button>
        </form>
      </Card>

      <StateBoundary loading={clientCardQuery.isLoading} error={clientCardQuery.error?.message}>
        {clientCardQuery.data ? (
          <DetailLayout
            aside={
              <Card className="space-y-2 p-3">
                <h3 className="text-lg font-semibold text-neutral-900">Matches</h3>
                {clientCardQuery.data.matches.length ? (
                  <div className="space-y-1">
                    {clientCardQuery.data.matches.map((client) => (
                      <button
                        key={client.id}
                        type="button"
                        onClick={() => setClientId(client.id)}
                        className="w-full rounded-md border border-neutral-200 p-2 text-left"
                        data-ui="interactive"
                      >
                        <p className="text-sm font-medium text-neutral-900">{client.name}</p>
                        <p className="text-xs text-neutral-600">{formatPhoneForDisplay(client.phone)}</p>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-neutral-600">No matches.</p>
                )}
              </Card>
            }
          >
            <Card className="space-y-2 p-3">
              {clientCardQuery.data.selectedClient ? (
                <>
                  <h2 className="text-xl font-semibold text-neutral-900">{clientCardQuery.data.selectedClient.name}</h2>
                  <p className="text-sm text-neutral-700">Phone: {formatPhoneForDisplay(clientCardQuery.data.selectedClient.phone)}</p>
                  <p className="text-sm text-neutral-700">Email: {clientCardQuery.data.selectedClient.email ?? "-"}</p>
                  <p className="text-sm text-neutral-700">Comment: {clientCardQuery.data.selectedClient.comment ?? "-"}</p>

                  <div className="space-y-1 pt-2">
                    <h3 className="text-base font-semibold text-neutral-900">Order history</h3>
                    {clientCardQuery.data.historyOrders.length ? (
                      clientCardQuery.data.historyOrders.map((order) => (
                        <div key={order.id} className="rounded-md border border-neutral-200 p-2">
                          <div className="flex items-start justify-between gap-1">
                            <div>
                              <p className="text-sm font-medium text-neutral-900">{order.description}</p>
                              <p className="text-xs text-neutral-600">{new Date(order.createdAt).toLocaleString()}</p>
                            </div>
                            <OrderStatusBadge status={order.status} />
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-neutral-600">No orders.</p>
                    )}
                  </div>
                </>
              ) : (
                <p className="text-sm text-neutral-600">Select a client from search results.</p>
              )}
            </Card>
          </DetailLayout>
        ) : null}
      </StateBoundary>
    </PageLayout>
  );
}
