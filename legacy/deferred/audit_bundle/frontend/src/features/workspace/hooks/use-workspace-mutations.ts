import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  changeOrderStatus,
  createClient,
  createWorkflowOrder,
  markOrderPaid,
  updateClient,
  updateOrder,
  workspaceQueryKeys
} from "@/features/workspace/api";
import type {
  CreateClientPayload,
  CreateWorkflowOrderPayload,
  OrderStatus,
  UpdateClientPayload,
  UpdateOrderPayload
} from "@/features/workspace/types";
import { useAccess } from "@/features/access/hooks/use-access";
import type { PermissionAction } from "@/features/rbac/types/rbac-types";
import type { PlanLimitType } from "@/features/subscription/types/subscription-types";
import { ApiClientError, type ApiClientError as ApiErrorType } from "@/shared/api/client";

function invalidateWorkspace(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: ["workspace"] });
}

function assertAccess(
  allowed: boolean,
  params: {
    permission: PermissionAction;
    limitType?: PlanLimitType;
  }
): void {
  if (allowed) {
    return;
  }

  throw new ApiClientError({
    message: "Permission denied",
    status: 403,
    code: params.limitType ? "plan_limit_exceeded" : "permission_denied",
    details: {
      permission: params.permission,
      ...(params.limitType
        ? {
            limitType: params.limitType
          }
        : {})
    }
  });
}

export function useCreateWorkflowOrderMutation() {
  const queryClient = useQueryClient();
  const { canAccess } = useAccess();

  return useMutation<{ orderId: string }, ApiErrorType, CreateWorkflowOrderPayload>({
    mutationFn: async (payload) => {
      assertAccess(canAccess("orders.create", { limitType: "maxOrdersPerMonth", increment: 1 }), {
        permission: "orders.create",
        limitType: "maxOrdersPerMonth"
      });

      return createWorkflowOrder(payload);
    },
    onSuccess: () => {
      invalidateWorkspace(queryClient);
    }
  });
}

export function useCreateClientMutation() {
  const queryClient = useQueryClient();
  const { canAccess } = useAccess();

  return useMutation<unknown, ApiErrorType, CreateClientPayload>({
    mutationFn: async (payload) => {
      assertAccess(canAccess("clients.create"), {
        permission: "clients.create"
      });

      return createClient(payload);
    },
    onSuccess: () => {
      invalidateWorkspace(queryClient);
    }
  });
}

export function useUpdateClientMutation() {
  const queryClient = useQueryClient();
  const { canAccess } = useAccess();

  return useMutation<unknown, ApiErrorType, UpdateClientPayload>({
    mutationFn: async (payload) => {
      assertAccess(canAccess("clients.edit"), {
        permission: "clients.edit"
      });

      return updateClient(payload);
    },
    onSuccess: () => {
      invalidateWorkspace(queryClient);
    }
  });
}

export function useUpdateOrderMutation() {
  const queryClient = useQueryClient();
  const { canAccess } = useAccess();

  return useMutation<unknown, ApiErrorType, UpdateOrderPayload>({
    mutationFn: async (payload) => {
      assertAccess(canAccess("orders.edit"), {
        permission: "orders.edit"
      });

      return updateOrder(payload);
    },
    onSuccess: () => {
      invalidateWorkspace(queryClient);
    }
  });
}

export function useChangeOrderStatusMutation() {
  const queryClient = useQueryClient();
  const { canAccess } = useAccess();

  return useMutation<void, ApiErrorType, { orderId: string; status: OrderStatus }>({
    mutationFn: async (payload) => {
      assertAccess(canAccess("orders.change_status"), {
        permission: "orders.change_status"
      });

      await changeOrderStatus(payload.orderId, payload.status);
    },
    onSuccess: () => {
      invalidateWorkspace(queryClient);
    }
  });
}

export function usePayOrderMutation() {
  const queryClient = useQueryClient();
  const { canAccess } = useAccess();

  return useMutation<void, ApiErrorType, { orderId: string }>({
    mutationFn: async ({ orderId }) => {
      assertAccess(canAccess("finance.create_payment", { limitType: "maxPaymentsPerMonth", increment: 1 }), {
        permission: "finance.create_payment",
        limitType: "maxPaymentsPerMonth"
      });

      await markOrderPaid(orderId);
    },
    onSuccess: () => {
      invalidateWorkspace(queryClient);
    }
  });
}

