import { apiClient } from "@/shared/api/client";
import type {
  CashDeskView,
  ClientCardView,
  ClientRecord,
  CreateClientPayload,
  CreateWorkflowOrderPayload,
  DashboardView,
  OrderRecord,
  OrderStatus,
  PagedResponse,
  TodayView,
  UpdateClientPayload,
  UpdateOrderPayload,
  WorkspaceListParams
} from "@/features/workspace/types";

export const workspaceQueryKeys = {
  dashboard: ["workspace", "dashboard"] as const,
  today: ["workspace", "today"] as const,
  cashDesk: ["workspace", "cashDesk"] as const,
  clientsSearch: (q: string) => ["workspace", "clients", "search", q] as const,
  clientsList: (q: string, limit: number, offset: number) => ["workspace", "clients", "list", q, limit, offset] as const,
  ordersList: (q: string, limit: number, offset: number) => ["workspace", "orders", "list", q, limit, offset] as const,
  clientCard: (q: string, clientId?: string) => ["workspace", "clientCard", q, clientId ?? ""] as const
};

export async function fetchDashboard(): Promise<DashboardView> {
  const response = await apiClient.get<DashboardView>("/api/workspace/dashboard");
  return response.data;
}

export async function fetchToday(): Promise<TodayView> {
  const response = await apiClient.get<TodayView>("/api/workspace/today");
  return response.data;
}

export async function fetchCashDesk(): Promise<CashDeskView> {
  const response = await apiClient.get<CashDeskView>("/api/workspace/cash-desk");
  return response.data;
}

export async function fetchClients(params: WorkspaceListParams): Promise<PagedResponse<ClientRecord>> {
  const response = await apiClient.get<PagedResponse<ClientRecord>>("/api/workspace/clients", {
    params: {
      q: params.q ?? "",
      limit: params.limit ?? 20,
      offset: params.offset ?? 0
    }
  });
  return response.data;
}

export async function createClient(payload: CreateClientPayload): Promise<ClientRecord> {
  const response = await apiClient.post<ClientRecord>("/api/workspace/clients", payload);
  return response.data;
}

export async function updateClient(payload: UpdateClientPayload): Promise<ClientRecord> {
  const response = await apiClient.patch<ClientRecord>(`/api/workspace/clients/${payload.clientId}`, {
    name: payload.name,
    phone: payload.phone,
    email: payload.email,
    comment: payload.comment,  });

  return response.data;
}

export async function fetchOrders(params: WorkspaceListParams): Promise<PagedResponse<OrderRecord>> {
  const response = await apiClient.get<PagedResponse<OrderRecord>>("/api/workspace/orders", {
    params: {
      q: params.q ?? "",
      limit: params.limit ?? 20,
      offset: params.offset ?? 0
    }
  });
  return response.data;
}

export async function searchClients(q: string, limit = 8): Promise<PagedResponse<ClientRecord>> {
  const response = await fetchClients({ q, limit, offset: 0 });
  return response;
}

export async function fetchClientCard(params: { q?: string; clientId?: string }): Promise<ClientCardView> {
  const response = await apiClient.get<ClientCardView>("/api/workspace/client-card", {
    params: {
      q: params.q ?? "",
      clientId: params.clientId
    }
  });
  return response.data;
}

export async function createWorkflowOrder(payload: CreateWorkflowOrderPayload): Promise<{ orderId: string }> {
  const response = await apiClient.post<{ orderId: string }>("/api/workspace/orders", payload);
  return response.data;
}

export async function updateOrder(payload: UpdateOrderPayload): Promise<OrderRecord> {
  const response = await apiClient.patch<OrderRecord>(`/api/workspace/orders/${payload.orderId}`, {
    description: payload.description,
    price: payload.price,
    status: payload.status
  });

  return response.data;
}

export async function changeOrderStatus(orderId: string, status: OrderStatus): Promise<void> {
  await apiClient.patch(`/api/workspace/orders/${orderId}/status`, { status });
}

export async function markOrderPaid(orderId: string): Promise<void> {
  await apiClient.post(`/api/workspace/orders/${orderId}/pay`);
}




