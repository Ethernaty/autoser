import type { WorkOrderListParams, WorkOrderListResponse } from "@/features/workspace/types/mvp-types";
import { apiClient } from "@/shared/api/client";
import type {
  ClientCreatePayload,
  ClientRecord,
  ClientUpdatePayload,
  DashboardAnalytics,
  DashboardAssigneeScope,
  DashboardPreferences,
  DashboardPreferencesUpdatePayload,
  DashboardStatusScope,
  DashboardSummary,
  EmployeeCreatePayload,
  EmployeeRecord,
  EmployeeUpdatePayload,
  OrderLineCreatePayload,
  OrderLineUpdatePayload,
  PagedResponse,
  PaymentCreatePayload,
  PaymentRecord,
  VehicleCreatePayload,
  VehicleRecord,
  WorkOrderHistoryItem,
  SupportTicketCreatePayload,
  SupportTicketListResponse,
  SupportTicketRecord,
  SupportTicketStatus,
  WorkOrderTimelineEvent,
  VehicleUpdatePayload,
  WorkOrderCreatePayload,
  WorkOrderOrderLine,
  WorkOrderRecord,
  WorkOrderStatus,
  WorkOrderUpdatePayload,
  WorkspaceContextResponse,
  WorkspaceSettingsResponse,
  WorkspaceSettingsUpdatePayload
} from "@/features/workspace/types/mvp-types";

export const mvpQueryKeys = {
  workspaceContext: ["workspace", "context"] as const,
  workspaceSettings: ["workspace", "settings"] as const,
  dashboardPreferences: ["workspace", "dashboard", "preferences"] as const,
  dashboardSummary: ["workspace", "dashboard", "summary"] as const,
  dashboardAnalytics: (months: number, statusScope: DashboardStatusScope = "all", assigneeScope: DashboardAssigneeScope = "all") =>
    ["workspace", "dashboard", "analytics", months, statusScope, assigneeScope] as const,
  clients: (q: string, limit: number, offset: number) => ["clients", q, limit, offset] as const,
  client: (clientId: string) => ["clients", "detail", clientId] as const,
  clientWorkOrders: (clientId: string, limit: number, offset: number) =>
    ["clients", "work-orders", clientId, limit, offset] as const,
  vehicles: (q: string, clientId: string, limit: number, offset: number) => ["vehicles", q, clientId, limit, offset] as const,
  vehiclesByClient: (clientId: string) => ["vehicles", "by-client", clientId] as const,
  vehicle: (vehicleId: string) => ["vehicles", "detail", vehicleId] as const,
  vehicleHistory: (vehicleId: string, limit: number, offset: number) => ["vehicles", "history", vehicleId, limit, offset] as const,
  vehicleWorkOrders: (vehicleId: string) => ["vehicles", "work-orders", vehicleId] as const,
  employees: (q: string, role: string, limit: number, offset: number) => ["employees", q, role, limit, offset] as const,
  employee: (employeeId: string) => ["employees", "detail", employeeId] as const,
  workOrders: (
    q: string,
    limit: number,
    offset: number,
    statusScope: DashboardStatusScope = "all",
    assigneeScope: DashboardAssigneeScope = "all"
  ) => ["work-orders", q, limit, offset, statusScope, assigneeScope] as const,
  workOrder: (workOrderId: string) => ["work-orders", "detail", workOrderId] as const,
  workOrderTimeline: (workOrderId: string, limit: number, offset: number) =>
    ["work-orders", workOrderId, "timeline", limit, offset] as const,
  workOrderLines: (workOrderId: string) => ["work-orders", workOrderId, "lines"] as const,
  workOrderPayments: (workOrderId: string) => ["work-orders", workOrderId, "payments"] as const,
  supportTickets: (q: string, status: string, category: string, myOnly: boolean, limit: number, offset: number) =>
    ["support", "tickets", q, status, category, myOnly, limit, offset] as const
};

function sanitizePositiveInt(value: number | undefined, fallback: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return fallback;
  const normalized = Math.trunc(value as number);
  if (normalized < min) return min;
  if (normalized > max) return max;
  return normalized;
}

export async function fetchWorkspaceContext(): Promise<WorkspaceContextResponse> {
  const response = await apiClient.get<WorkspaceContextResponse>("/api/workspace/context");
  return response.data;
}

export async function fetchWorkspaceSettings(): Promise<WorkspaceSettingsResponse> {
  const response = await apiClient.get<WorkspaceSettingsResponse>("/api/workspace/settings");
  return response.data;
}

export async function updateWorkspaceSettings(payload: WorkspaceSettingsUpdatePayload): Promise<WorkspaceSettingsResponse> {
  const response = await apiClient.patch<WorkspaceSettingsResponse>("/api/workspace/settings", payload);
  return response.data;
}

export async function fetchDashboardSummary(recentLimit = 10): Promise<DashboardSummary> {
  const response = await apiClient.get<DashboardSummary>("/api/workspace/dashboard/summary", {
    params: { recent_limit: recentLimit }
  });
  return response.data;
}

export async function fetchDashboardPreferences(): Promise<DashboardPreferences> {
  const response = await apiClient.get<DashboardPreferences>("/api/workspace/dashboard/preferences");
  return response.data;
}

export async function updateDashboardPreferences(payload: DashboardPreferencesUpdatePayload): Promise<DashboardPreferences> {
  const response = await apiClient.patch<DashboardPreferences>("/api/workspace/dashboard/preferences", payload);
  return response.data;
}

export async function fetchDashboardAnalytics(params?: {
  months?: number;
  status_scope?: DashboardStatusScope;
  assignee_scope?: DashboardAssigneeScope;
}): Promise<DashboardAnalytics> {
  const response = await apiClient.get<DashboardAnalytics>("/api/workspace/dashboard/analytics", {
    params: {
      months: params?.months ?? 12,
      status_scope: params?.status_scope ?? "all",
      assignee_scope: params?.assignee_scope ?? "all"
    }
  });
  return response.data;
}

export async function fetchClients(params: { q?: string; limit?: number; offset?: number }): Promise<PagedResponse<ClientRecord>> {
  const response = await apiClient.get<PagedResponse<ClientRecord>>("/api/workspace/clients", {
    params: {
      q: params.q ?? "",
      limit: params.limit ?? 20,
      offset: params.offset ?? 0
    }
  });
  return response.data;
}

export async function fetchClient(clientId: string): Promise<ClientRecord> {
  const response = await apiClient.get<ClientRecord>(`/api/workspace/clients/${clientId}`);
  return response.data;
}

export async function fetchClientWorkOrders(
  clientId: string,
  params?: { limit?: number; offset?: number }
): Promise<WorkOrderHistoryItem[]> {
  const response = await apiClient.get<WorkOrderHistoryItem[]>(`/api/workspace/clients/${clientId}/work-orders`, {
    params: {
      limit: params?.limit ?? 20,
      offset: params?.offset ?? 0
    }
  });
  return response.data;
}

export async function createClient(payload: ClientCreatePayload): Promise<ClientRecord> {
  const response = await apiClient.post<ClientRecord>("/api/workspace/clients", payload);
  return response.data;
}

export async function updateClient(clientId: string, payload: ClientUpdatePayload): Promise<ClientRecord> {
  const response = await apiClient.patch<ClientRecord>(`/api/workspace/clients/${clientId}`, payload);
  return response.data;
}

export async function fetchVehicles(params: {
  q?: string;
  client_id?: string;
  limit?: number;
  offset?: number;
}): Promise<PagedResponse<VehicleRecord>> {
  const response = await apiClient.get<PagedResponse<VehicleRecord>>("/api/workspace/vehicles", {
    params: {
      q: params.q ?? "",
      client_id: params.client_id,
      limit: params.limit ?? 20,
      offset: params.offset ?? 0
    }
  });
  return response.data;
}

export async function fetchVehiclesByClient(clientId: string): Promise<VehicleRecord[]> {
  const response = await apiClient.get<VehicleRecord[]>(`/api/workspace/vehicles/by-client/${clientId}`);
  return response.data;
}

export async function fetchVehicle(vehicleId: string): Promise<VehicleRecord> {
  const response = await apiClient.get<VehicleRecord>(`/api/workspace/vehicles/${vehicleId}`);
  return response.data;
}

export async function fetchVehicleHistory(
  vehicleId: string,
  params?: { limit?: number; offset?: number }
): Promise<WorkOrderHistoryItem[]> {
  const response = await apiClient.get<WorkOrderHistoryItem[]>(`/api/workspace/vehicles/${vehicleId}/history`, {
    params: {
      limit: params?.limit ?? 50,
      offset: params?.offset ?? 0
    }
  });
  return response.data;
}

export async function createVehicle(payload: VehicleCreatePayload): Promise<VehicleRecord> {
  const response = await apiClient.post<VehicleRecord>("/api/workspace/vehicles", payload);
  return response.data;
}

export async function updateVehicle(vehicleId: string, payload: VehicleUpdatePayload): Promise<VehicleRecord> {
  const response = await apiClient.patch<VehicleRecord>(`/api/workspace/vehicles/${vehicleId}`, payload);
  return response.data;
}

export async function fetchVehicleWorkOrders(vehicleId: string, params?: { limit?: number; offset?: number }): Promise<WorkOrderRecord[]> {
  const response = await apiClient.get<WorkOrderRecord[]>(`/api/workspace/vehicles/${vehicleId}/work-orders`, {
    params: {
      limit: params?.limit ?? 20,
      offset: params?.offset ?? 0
    }
  });
  return response.data;
}

export async function fetchEmployees(params: {
  q?: string;
  role?: string;
  limit?: number;
  offset?: number;
}): Promise<PagedResponse<EmployeeRecord>> {
  const limit = sanitizePositiveInt(params.limit, 20, 1, 50);
  const offset = sanitizePositiveInt(params.offset, 0, 0, 100000);
  const response = await apiClient.get<PagedResponse<EmployeeRecord>>("/api/workspace/employees", {
    params: {
      q: params.q ?? "",
      role: params.role,
      limit,
      offset
    }
  });
  return response.data;
}

export async function fetchEmployee(employeeId: string): Promise<EmployeeRecord> {
  const response = await apiClient.get<EmployeeRecord>(`/api/workspace/employees/${employeeId}`);
  return response.data;
}

export async function createEmployee(payload: EmployeeCreatePayload): Promise<EmployeeRecord> {
  const response = await apiClient.post<EmployeeRecord>("/api/workspace/employees", payload);
  return response.data;
}

export async function updateEmployee(employeeId: string, payload: EmployeeUpdatePayload): Promise<EmployeeRecord> {
  const response = await apiClient.patch<EmployeeRecord>(`/api/workspace/employees/${employeeId}`, payload);
  return response.data;
}

export async function setEmployeeStatus(employeeId: string, isActive: boolean): Promise<EmployeeRecord> {
  const response = await apiClient.patch<EmployeeRecord>(`/api/workspace/employees/${employeeId}/status`, {
    is_active: isActive
  });
  return response.data;
}

export async function fetchWorkOrders(params: WorkOrderListParams): Promise<WorkOrderListResponse> {
  const response = await apiClient.get<WorkOrderListResponse>("/api/workspace/work-orders", { params });
  return response.data;
}

export async function fetchWorkOrder(workOrderId: string): Promise<WorkOrderRecord> {
  const response = await apiClient.get<WorkOrderRecord>(`/api/workspace/work-orders/${workOrderId}`);
  return response.data;
}

export async function fetchWorkOrderTimeline(
  workOrderId: string,
  params?: { limit?: number; offset?: number }
): Promise<WorkOrderTimelineEvent[]> {
  const response = await apiClient.get<WorkOrderTimelineEvent[]>(`/api/workspace/work-orders/${workOrderId}/timeline`, {
    params: {
      limit: params?.limit ?? 100,
      offset: params?.offset ?? 0
    }
  });
  return response.data;
}

export async function addWorkOrderTimelineComment(workOrderId: string, comment: string): Promise<void> {
  await apiClient.post(`/api/workspace/work-orders/${workOrderId}/timeline/comments`, { comment });
}

export async function createWorkOrder(payload: WorkOrderCreatePayload): Promise<WorkOrderRecord> {
  const response = await apiClient.post<WorkOrderRecord>("/api/workspace/work-orders", payload);
  return response.data;
}

export async function updateWorkOrder(workOrderId: string, payload: WorkOrderUpdatePayload): Promise<WorkOrderRecord> {
  const response = await apiClient.patch<WorkOrderRecord>(`/api/workspace/work-orders/${workOrderId}`, payload);
  return response.data;
}

export async function setWorkOrderStatus(workOrderId: string, status: WorkOrderStatus): Promise<WorkOrderRecord> {
  const response = await apiClient.post<WorkOrderRecord>(`/api/workspace/work-orders/${workOrderId}/status`, { status });
  return response.data;
}

export async function assignWorkOrder(workOrderId: string, employeeIds: string[]): Promise<WorkOrderRecord> {
  const response = await apiClient.post<WorkOrderRecord>(`/api/workspace/work-orders/${workOrderId}/assign`, {
    employee_ids: employeeIds
  });
  return response.data;
}

export async function attachWorkOrderVehicle(workOrderId: string, vehicleId: string): Promise<WorkOrderRecord> {
  const response = await apiClient.post<WorkOrderRecord>(`/api/workspace/work-orders/${workOrderId}/attach-vehicle`, {
    vehicle_id: vehicleId
  });
  return response.data;
}

export async function closeWorkOrder(workOrderId: string): Promise<WorkOrderRecord> {
  const response = await apiClient.post<WorkOrderRecord>(`/api/workspace/work-orders/${workOrderId}/close`);
  return response.data;
}

export async function fetchWorkOrderLines(workOrderId: string): Promise<WorkOrderOrderLine[]> {
  const response = await apiClient.get<WorkOrderOrderLine[]>(`/api/workspace/work-orders/${workOrderId}/lines`);
  return response.data;
}

export async function addWorkOrderLine(workOrderId: string, payload: OrderLineCreatePayload): Promise<WorkOrderOrderLine> {
  const response = await apiClient.post<WorkOrderOrderLine>(`/api/workspace/work-orders/${workOrderId}/lines`, payload);
  return response.data;
}

export async function updateWorkOrderLine(
  workOrderId: string,
  lineId: string,
  payload: OrderLineUpdatePayload
): Promise<WorkOrderOrderLine> {
  const response = await apiClient.patch<WorkOrderOrderLine>(`/api/workspace/work-orders/${workOrderId}/lines/${lineId}`, payload);
  return response.data;
}

export async function deleteWorkOrderLine(workOrderId: string, lineId: string): Promise<void> {
  await apiClient.delete(`/api/workspace/work-orders/${workOrderId}/lines/${lineId}`);
}

export async function fetchWorkOrderPayments(workOrderId: string): Promise<PaymentRecord[]> {
  const response = await apiClient.get<PaymentRecord[]>(`/api/workspace/work-orders/${workOrderId}/payments`);
  return response.data;
}

export async function createWorkOrderPayment(workOrderId: string, payload: PaymentCreatePayload): Promise<PaymentRecord> {
  const response = await apiClient.post<PaymentRecord>(`/api/workspace/work-orders/${workOrderId}/payments`, payload);
  return response.data;
}

export async function fetchSupportTickets(params: {
  q?: string;
  status?: SupportTicketStatus;
  category?: string;
  my_only?: boolean;
  limit?: number;
  offset?: number;
}): Promise<SupportTicketListResponse> {
  const response = await apiClient.get<SupportTicketListResponse>("/api/workspace/support/tickets", {
    params: {
      q: params.q ?? "",
      status: params.status,
      category: params.category,
      my_only: params.my_only ?? false,
      limit: params.limit ?? 20,
      offset: params.offset ?? 0
    }
  });
  return response.data;
}

export async function createSupportTicket(payload: SupportTicketCreatePayload): Promise<SupportTicketRecord> {
  const response = await apiClient.post<SupportTicketRecord>("/api/workspace/support/tickets", payload);
  return response.data;
}

export async function updateSupportTicketStatus(ticketId: string, status: SupportTicketStatus): Promise<SupportTicketRecord> {
  const response = await apiClient.patch<SupportTicketRecord>(`/api/workspace/support/tickets/${ticketId}/status`, { status });
  return response.data;
}

export async function voidWorkOrderPayment(workOrderId: string, paymentId: string, reason: string): Promise<PaymentRecord> {
  const response = await apiClient.post<PaymentRecord>(`/api/workspace/work-orders/${workOrderId}/payments/${paymentId}/void`, { reason });
  return response.data;
}

export async function addSupportTicketMessage(ticketId: string, message: string): Promise<SupportTicketRecord> {
  const response = await apiClient.post<SupportTicketRecord>(`/api/workspace/support/tickets/${ticketId}/messages`, { message });
  return response.data;
}
