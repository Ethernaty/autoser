import type { PlanDefinition, SubscriptionPlan } from "@/features/subscription/types/subscription-types";

export const PLAN_DEFINITIONS: Readonly<Record<SubscriptionPlan, PlanDefinition>> = {
  free: {
    plan: "free",
    monthlyPrice: 0,
    featureFlags: {
      advancedAnalytics: false,
      refundsAllowed: false
    },
    usageLimits: {
      maxUsers: 3,
      maxOrdersPerMonth: 100,
      maxPaymentsPerMonth: 50
    }
  },
  basic: {
    plan: "basic",
    monthlyPrice: 49,
    featureFlags: {
      advancedAnalytics: false,
      refundsAllowed: false
    },
    usageLimits: {
      maxUsers: 7,
      maxOrdersPerMonth: 500,
      maxPaymentsPerMonth: 300
    }
  },
  pro: {
    plan: "pro",
    monthlyPrice: 129,
    featureFlags: {
      advancedAnalytics: true,
      refundsAllowed: true
    },
    usageLimits: {
      maxUsers: "unlimited",
      maxOrdersPerMonth: "unlimited",
      maxPaymentsPerMonth: "unlimited"
    }
  }
} as const;

export const BACKEND_PLAN_ALIASES: Readonly<Record<string, SubscriptionPlan>> = {
  free: "free",
  starter: "free",
  basic: "basic",
  standard: "basic",
  pro: "pro",
  premium: "pro",
  growth: "pro",
  enterprise: "pro"
};
