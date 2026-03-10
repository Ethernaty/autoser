"use client";

import { Button } from "@/design-system/primitives/button";
import { Card } from "@/design-system/primitives/card";
import { PageLayout, StateBoundary } from "@/design-system/patterns";
import { DisableIfNoAccess } from "@/features/access/ui/access-guard";
import { usePayOrderMutation, useWorkspaceCashDeskQuery } from "@/features/workspace/hooks";
import { OrderStatusBadge } from "@/features/workspace/ui/order-status-badge";

export function CashDeskScreen(): JSX.Element {
  const cashDeskQuery = useWorkspaceCashDeskQuery();
  const payMutation = usePayOrderMutation();

  return (
    <PageLayout title="Cash desk" subtitle={cashDeskQuery.data?.nowLabel ?? "Loading..."}>
      <StateBoundary loading={cashDeskQuery.isLoading} error={cashDeskQuery.error?.message}>
        {cashDeskQuery.data ? (
          <>
            <Card className="p-3">
              <p className="text-sm text-neutral-600">Total due</p>
              <p className="mt-1 text-[32px] leading-[40px] font-bold text-neutral-900">{cashDeskQuery.data.totalDue}</p>
            </Card>

            <Card className="space-y-2 p-3">
              <h2 className="text-lg font-semibold text-neutral-900">Ready for payment</h2>
              {cashDeskQuery.data.rows.length ? (
                cashDeskQuery.data.rows.map((row) => (
                  <div key={row.id} className="rounded-md border border-neutral-200 p-2">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="text-sm font-semibold text-neutral-900">{row.clientName}</p>
                        <p className="text-sm text-neutral-600">{row.description}</p>
                        <p className="text-xs text-neutral-500">{new Date(row.createdAt).toLocaleString()}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-base font-semibold text-neutral-900">{row.price}</p>
                        <OrderStatusBadge status={row.status} />
                      </div>
                    </div>
                    <div className="mt-2">
                      <DisableIfNoAccess permission="finance.create_payment" limitType="maxPaymentsPerMonth">
                        {(disabled, onUpgrade) => (
                          <div className="flex items-center gap-1">
                            <Button
                              size="sm"
                              disabled={disabled}
                              onClick={() => payMutation.mutate({ orderId: row.id })}
                              loading={payMutation.isPending}
                            >
                              Confirm payment
                            </Button>
                            {disabled ? (
                              <Button variant="quiet" size="sm" onClick={onUpgrade}>
                                Upgrade
                              </Button>
                            ) : null}
                          </div>
                        )}
                      </DisableIfNoAccess>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-neutral-600">No orders in cash desk queue.</p>
              )}
            </Card>
          </>
        ) : null}
      </StateBoundary>
    </PageLayout>
  );
}
