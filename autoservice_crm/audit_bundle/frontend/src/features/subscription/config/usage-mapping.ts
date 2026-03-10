import type { PlanLimitType, UsageCounterKey } from "@/features/subscription/types/subscription-types";

export const COUNTER_TO_LIMIT: Readonly<Record<UsageCounterKey, PlanLimitType>> = {
  ordersCreated: "maxOrdersPerMonth",
  usersCount: "maxUsers",
  paymentsCount: "maxPaymentsPerMonth"
};

export const LIMIT_TO_COUNTER: Readonly<Record<PlanLimitType, UsageCounterKey>> = {
  maxOrdersPerMonth: "ordersCreated",
  maxUsers: "usersCount",
  maxPaymentsPerMonth: "paymentsCount"
};

export const USAGE_COUNTER_ACTIONS: Readonly<Record<UsageCounterKey, string>> = {
  ordersCreated: "usage.orders_created.increment",
  usersCount: "usage.users_count.increment",
  paymentsCount: "usage.payments_count.increment"
};
