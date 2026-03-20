import { apiClient } from "@/shared/api/client";
import type {
  ClientCreatePayload,
  ClientRecord,
  ClientUpdatePayload,
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
  dashboardSummary: ["workspace", "dashboard", "summary"] as const,
  clients: (q: string, limit: number, offset: number) => ["clients", q, limit, offset] as const,
  client: (clientId: string) => ["clients", "detail", clientId] as const,
  vehicles: (q: string, clientId: string, limit: number, offset: number) => ["vehicles", q, clientId, limit, offset] as const,
  vehiclesByClient: (clientId: string) => ["vehicles", "by-client", clientId] as const,
  vehicle: (vehicleId: string) => ["vehicles", "detail", vehicleId] as const,
  vehicleWorkOrders: (vehicleId: string) => ["vehicles", "work-orders", vehicleId] as const,
  employees: (q: string, role: string, limit: number, offset: number) => ["employees", q, role, limit, offset] as const,
  employee: (employeeId: string) => ["employees", "detail", employeeId] as const,
  workOrders: (q: string, limit: number, offset: number) => ["work-orders", q, limit, offset] as const,
  workOrder: (workOrderId: string) => ["work-orders", "detail", workOrderId] as const,
  workOrderLines: (workOrderId: string) => ["work-orders", workOrderId, "lines"] as const,
  workOrderPayments: (workOrderId: string) => ["work-orders", workOrderId, "payments"] as const
};

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
  const response = await apiClient.get<PagedResponse<EmployeeRecord>>("/api/workspace/employees", {
    params: {
      q: params.q ?? "",
      role: params.role,
      limit: params.limit ?? 20,
      offset: params.offset ?? 0
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

export async function fetchWorkOrders(params: { q?: string; limit?: number; offset?: number }): Promise<PagedResponse<WorkOrderRecord>> {
  const response = await apiClient.get<PagedResponse<WorkOrderRecord>>("/api/workspace/work-orders", {
    params: {
      q: params.q ?? "",
      limit: params.limit ?? 20,
      offset: params.offset ?? 0
    }
  });
  return response.data;
}

export async function fetchWorkOrder(workOrderId: string): Promise<WorkOrderRecord> {
  const response = await apiClient.get<WorkOrderRecord>(`/api/workspace/work-orders/${workOrderId}`);
  return response.data;
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

export async function assignWorkOrder(workOrderId: string, employeeId: string | null): Promise<WorkOrderRecord> {
  const response = await apiClient.post<WorkOrderRecord>(`/api/workspace/work-orders/${workOrderId}/assign`, {
    employee_id: employeeId
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
