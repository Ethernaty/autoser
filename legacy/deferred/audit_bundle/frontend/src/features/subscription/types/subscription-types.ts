export const SUBSCRIPTION_PLANS = ["free", "basic", "pro"] as const;
export type SubscriptionPlan = (typeof SUBSCRIPTION_PLANS)[number];

export const SUBSCRIPTION_STATUSES = ["active", "past_due", "canceled", "trial"] as const;
export type SubscriptionStatus = (typeof SUBSCRIPTION_STATUSES)[number];

export const PLAN_LIMIT_TYPES = ["maxUsers", "maxOrdersPerMonth", "maxPaymentsPerMonth"] as const;
export type PlanLimitType = (typeof PLAN_LIMIT_TYPES)[number];

export const PLAN_FEATURE_FLAGS = ["advancedAnalytics", "refundsAllowed"] as const;
export type PlanFeatureFlag = (typeof PLAN_FEATURE_FLAGS)[number];

export const USAGE_COUNTER_KEYS = ["ordersCreated", "usersCount", "paymentsCount"] as const;
export type UsageCounterKey = (typeof USAGE_COUNTER_KEYS)[number];

export type LimitValue = number | "unlimited";

export type WorkspaceSubscription = {
  workspaceId: string;
  plan: SubscriptionPlan;
  status: SubscriptionStatus;
  currentPeriodStart: string;
  currentPeriodEnd: string;
  trialEndsAt: string | null;
  createdAt: string;
  updatedAt: string;
};

export type PlanDefinition = {
  plan: SubscriptionPlan;
  monthlyPrice: number;
  featureFlags: Readonly<Record<PlanFeatureFlag, boolean>>;
  usageLimits: Readonly<Record<PlanLimitType, LimitValue>>;
};

export type WorkspaceUsage = {
  workspaceId: string;
  month: string;
  ordersCreated: number;
  usersCount: number;
  paymentsCount: number;
};

export type PlanUsageCheck = {
  limitType: PlanLimitType;
  projectedIncrement?: number;
};

export type SubscriptionSnapshot = {
  subscription: WorkspaceSubscription;
  planDefinition: PlanDefinition;
  usage: WorkspaceUsage;
};

export type PlanCapabilities = {
  plan: SubscriptionPlan;
  status: SubscriptionStatus;
  featureFlags: Readonly<Record<PlanFeatureFlag, boolean>>;
  usageLimits: Readonly<Record<PlanLimitType, LimitValue>>;
  usage: WorkspaceUsage;
  remaining: Readonly<Record<PlanLimitType, number | "unlimited">>;
};

export type SubscriptionQueryResponse = {
  subscription: WorkspaceSubscription;
  planDefinition: PlanDefinition;
  usage: WorkspaceUsage;
  capabilities: PlanCapabilities;
};
