"use client";

import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { fetchSubscription, subscriptionQueryKeys } from "@/features/subscription/api/subscription-api";
import type { SubscriptionQueryResponse } from "@/features/subscription/types/subscription-types";
import type { ApiClientError } from "@/shared/api/client";

export function useSubscriptionQuery(): UseQueryResult<SubscriptionQueryResponse, ApiClientError> {
  return useQuery<SubscriptionQueryResponse, ApiClientError>({
    queryKey: subscriptionQueryKeys.current,
    queryFn: fetchSubscription,
    staleTime: 30_000
  });
}
