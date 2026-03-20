import { apiClient } from "@/shared/api/client";
import type { SubscriptionQueryResponse } from "@/features/subscription/types/subscription-types";

export const subscriptionQueryKeys = {
  current: ["subscription", "current"] as const
};

export async function fetchSubscription(): Promise<SubscriptionQueryResponse> {
  const response = await apiClient.get<SubscriptionQueryResponse>("/api/subscription");
  return response.data;
}
