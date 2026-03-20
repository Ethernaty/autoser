import "server-only";

import { backendRequest } from "@/shared/api/backend-client";
import { WorkspaceScopeError } from "@/shared/errors/workspace-scope-error";
import type { WorkspaceContext } from "@/features/auth/api/backend-session";
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

function authHeader(context: WorkspaceContext): Record<string, string> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${context.accessToken}`,
    "X-Workspace-Id": context.workspaceId
  };
  if (context.forwardedFor) {
    headers["X-Forwarded-For"] = context.forwardedFor;
  }
  return headers;
}

function assertTenantScope(context: WorkspaceContext, tenantId: string | undefined | null, entity: string): void {
  if (!tenantId || tenantId !== context.workspaceId) {
    throw new WorkspaceScopeError({
      expectedWorkspaceId: context.workspaceId,
      actualWorkspaceId: tenantId ?? null,
      entity
    });
  }
}

function assertTenantScopedPage<T extends { tenant_id: string }>(
  context: WorkspaceContext,
  payload: PagedResponse<T>,
  entity: string
): PagedResponse<T> {
  payload.items.forEach((item) => assertTenantScope(context, item.tenant_id, entity));
  return payload;
}

function assertTenantScopedItem<T extends { tenant_id: string }>(
  context: WorkspaceContext,
  payload: T,
  entity: string
): T {
  assertTenantScope(context, payload.tenant_id, entity);
  return payload;
}

export async function getWorkspaceContext(context: WorkspaceContext): Promise<WorkspaceContextResponse> {
  return backendRequest<WorkspaceContextResponse>("/workspace/context", {
    method: "GET",
    headers: authHeader(context)
  });
}

export async function getWorkspaceSettings(context: WorkspaceContext): Promise<WorkspaceSettingsResponse> {
  const settings = await backendRequest<WorkspaceSettingsResponse>("/workspace/settings", {
    method: "GET",
    headers: authHeader(context)
  });
  return assertTenantScopedItem(context, settings, "workspace_settings");
}

export async function patchWorkspaceSettings(
  context: WorkspaceContext,
  payload: WorkspaceSettingsUpdatePayload
): Promise<WorkspaceSettingsResponse> {
  const settings = await backendRequest<WorkspaceSettingsResponse>("/workspace/settings", {
    method: "PATCH",
    headers: authHeader(context),
    body: JSON.stringify(payload)
  });
  return assertTenantScopedItem(context, settings, "workspace_settings");
}

export async function getDashboardSummary(context: WorkspaceContext, recentLimit = 10): Promise<DashboardSummary> {
  const query = new URLSearchParams();
  query.set("recent_limit", String(Math.min(50, Math.max(1, recentLimit))));
  return backendRequest<DashboardSummary>(`/dashboard/summary?${query.toString()}`, {
    method: "GET",
    headers: authHeader(context)
  });
}

export async function listClients(
  context: WorkspaceContext,
  params: { q?: string; limit?: number; offset?: number }
): Promise<PagedResponse<ClientRecord>> {
  const query = new URLSearchParams();
  if (params.q) {
    query.set("q", params.q);
  }
  query.set("limit", String(params.limit ?? 20));
  query.set("offset", String(params.offset ?? 0));

  const page = await backendRequest<PagedResponse<ClientRecord>>(`/clients/?${query.toString()}`, {
    method: "GET",
    headers: authHeader(context)
  });

  return assertTenantScopedPage(context, page, "clients");
}

export async function getClient(context: WorkspaceContext, clientId: string): Promise<ClientRecord> {
  const client = await backendRequest<ClientRecord>(`/clients/${clientId}`, {
    method: "GET",
    headers: authHeader(context)
  });
  return assertTenantScopedItem(context, client, "client");
}

export async function createClient(
  context: WorkspaceContext,
  payload: ClientCreatePayload,
  options?: { idempotencyKey?: string }
): Promise<ClientRecord> {
  const headers = authHeader(context);
  if (options?.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }

  const client = await backendRequest<ClientRecord>("/clients/", {
    method: "POST",
    headers,
    body: JSON.stringify(payload)
  });
  return assertTenantScopedItem(context, client, "client");
}

export async function patchClient(
  context: WorkspaceContext,
  clientId: string,
  payload: ClientUpdatePayload
): Promise<ClientRecord> {
  const client = await backendRequest<ClientRecord>(`/clients/${clientId}`, {
    method: "PATCH",
    headers: authHeader(context),
    body: JSON.stringify(payload)
  });
  return assertTenantScopedItem(context, client, "client");
}

export async function listVehicles(
  context: WorkspaceContext,
  params: { q?: string; client_id?: string; limit?: number; offset?: number }
): Promise<PagedResponse<VehicleRecord>> {
  const query = new URLSearchParams();
  if (params.q) {
    query.set("q", params.q);
  }
  if (params.client_id) {
    query.set("client_id", params.client_id);
  }
  query.set("limit", String(params.limit ?? 20));
  query.set("offset", String(params.offset ?? 0));

  const page = await backendRequest<PagedResponse<VehicleRecord>>(`/vehicles/?${query.toString()}`, {
    method: "GET",
    headers: authHeader(context)
  });

  return assertTenantScopedPage(context, page, "vehicles");
}

export async function listVehiclesByClient(context: WorkspaceContext, clientId: string): Promise<VehicleRecord[]> {
  const payload = await backendRequest<VehicleRecord[]>(`/vehicles/by-client/${clientId}`, {
    method: "GET",
    headers: authHeader(context)
  });
  payload.forEach((item) => assertTenantScope(context, item.tenant_id, "vehicle"));
  return payload;
}

export async function getVehicle(context: WorkspaceContext, vehicleId: string): Promise<VehicleRecord> {
  const payload = await backendRequest<VehicleRecord>(`/vehicles/${vehicleId}`, {
    method: "GET",
    headers: authHeader(context)
  });
  return assertTenantScopedItem(context, payload, "vehicle");
}

export async function createVehicle(
  context: WorkspaceContext,
  payload: VehicleCreatePayload,
  options?: { idempotencyKey?: string }
): Promise<VehicleRecord> {
  const headers = authHeader(context);
  if (options?.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }
  const vehicle = await backendRequest<VehicleRecord>("/vehicles/", {
    method: "POST",
    headers,
    body: JSON.stringify(payload)
  });
  return assertTenantScopedItem(context, vehicle, "vehicle");
}

export async function patchVehicle(
  context: WorkspaceContext,
  vehicleId: string,
  payload: VehicleUpdatePayload
): Promise<VehicleRecord> {
  const vehicle = await backendRequest<VehicleRecord>(`/vehicles/${vehicleId}`, {
    method: "PATCH",
    headers: authHeader(context),
    body: JSON.stringify(payload)
  });
  return assertTenantScopedItem(context, vehicle, "vehicle");
}

export async function listVehicleWorkOrders(
  context: WorkspaceContext,
  vehicleId: string,
  params: { limit?: number; offset?: number }
): Promise<WorkOrderRecord[]> {
  const query = new URLSearchParams();
  query.set("limit", String(params.limit ?? 20));
  query.set("offset", String(params.offset ?? 0));
  const payload = await backendRequest<WorkOrderRecord[]>(`/vehicles/${vehicleId}/work-orders?${query.toString()}`, {
    method: "GET",
    headers: authHeader(context)
  });
  payload.forEach((item) => assertTenantScope(context, item.tenant_id, "work_order"));
  return payload;
}

export async function listEmployees(
  context: WorkspaceContext,
  params: { q?: string; role?: string; limit?: number; offset?: number }
): Promise<PagedResponse<EmployeeRecord>> {
  const query = new URLSearchParams();
  if (params.q) {
    query.set("q", params.q);
  }
  if (params.role) {
    query.set("role", params.role);
  }
  query.set("limit", String(params.limit ?? 20));
  query.set("offset", String(params.offset ?? 0));

  const payload = await backendRequest<PagedResponse<EmployeeRecord>>(`/employees/?${query.toString()}`, {
    method: "GET",
    headers: authHeader(context)
  });
  payload.items.forEach((item) => assertTenantScope(context, item.tenant_id, "employee"));
  return payload;
}

export async function getEmployee(context: WorkspaceContext, employeeId: string): Promise<EmployeeRecord> {
  const payload = await backendRequest<EmployeeRecord>(`/employees/${employeeId}`, {
    method: "GET",
    headers: authHeader(context)
  });
  assertTenantScope(context, payload.tenant_id, "employee");
  return payload;
}

export async function createEmployee(
  context: WorkspaceContext,
  payload: EmployeeCreatePayload,
  options?: { idempotencyKey?: string }
): Promise<EmployeeRecord> {
  const headers = authHeader(context);
  if (options?.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }
  const employee = await backendRequest<EmployeeRecord>("/employees/", {
    method: "POST",
    headers,
    body: JSON.stringify(payload)
  });
  assertTenantScope(context, employee.tenant_id, "employee");
  return employee;
}

export async function patchEmployee(
  context: WorkspaceContext,
  employeeId: string,
  payload: EmployeeUpdatePayload
): Promise<EmployeeRecord> {
  const employee = await backendRequest<EmployeeRecord>(`/employees/${employeeId}`, {
    method: "PATCH",
    headers: authHeader(context),
    body: JSON.stringify(payload)
  });
  assertTenantScope(context, employee.tenant_id, "employee");
  return employee;
}

export async function patchEmployeeStatus(
  context: WorkspaceContext,
  employeeId: string,
  isActive: boolean
): Promise<EmployeeRecord> {
  const employee = await backendRequest<EmployeeRecord>(`/employees/${employeeId}/status`, {
    method: "PATCH",
    headers: authHeader(context),
    body: JSON.stringify({ is_active: isActive })
  });
  assertTenantScope(context, employee.tenant_id, "employee");
  return employee;
}

export async function listWorkOrders(
  context: WorkspaceContext,
  params: { q?: string; limit?: number; offset?: number }
): Promise<PagedResponse<WorkOrderRecord>> {
  const query = new URLSearchParams();
  if (params.q) {
    query.set("q", params.q);
  }
  query.set("limit", String(params.limit ?? 20));
  query.set("offset", String(params.offset ?? 0));

  const payload = await backendRequest<PagedResponse<WorkOrderRecord>>(`/work-orders/?${query.toString()}`, {
    method: "GET",
    headers: authHeader(context)
  });
  payload.items.forEach((item) => assertTenantScope(context, item.tenant_id, "work_order"));
  return payload;
}

export async function getWorkOrder(context: WorkspaceContext, workOrderId: string): Promise<WorkOrderRecord> {
  const payload = await backendRequest<WorkOrderRecord>(`/work-orders/${workOrderId}`, {
    method: "GET",
    headers: authHeader(context)
  });
  assertTenantScope(context, payload.tenant_id, "work_order");
  return payload;
}

export async function createWorkOrder(
  context: WorkspaceContext,
  payload: WorkOrderCreatePayload,
  options?: { idempotencyKey?: string }
): Promise<WorkOrderRecord> {
  const headers = authHeader(context);
  if (options?.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }
  const workOrder = await backendRequest<WorkOrderRecord>("/work-orders/", {
    method: "POST",
    headers,
    body: JSON.stringify(payload)
  });
  assertTenantScope(context, workOrder.tenant_id, "work_order");
  return workOrder;
}

export async function patchWorkOrder(
  context: WorkspaceContext,
  workOrderId: string,
  payload: WorkOrderUpdatePayload
): Promise<WorkOrderRecord> {
  const workOrder = await backendRequest<WorkOrderRecord>(`/work-orders/${workOrderId}`, {
    method: "PATCH",
    headers: authHeader(context),
    body: JSON.stringify(payload)
  });
  assertTenantScope(context, workOrder.tenant_id, "work_order");
  return workOrder;
}

export async function setWorkOrderStatus(
  context: WorkspaceContext,
  workOrderId: string,
  status: WorkOrderStatus
): Promise<WorkOrderRecord> {
  const workOrder = await backendRequest<WorkOrderRecord>(`/work-orders/${workOrderId}/status`, {
    method: "POST",
    headers: authHeader(context),
    body: JSON.stringify({ status })
  });
  assertTenantScope(context, workOrder.tenant_id, "work_order");
  return workOrder;
}

export async function assignWorkOrder(
  context: WorkspaceContext,
  workOrderId: string,
  employeeId: string | null
): Promise<WorkOrderRecord> {
  const workOrder = await backendRequest<WorkOrderRecord>(`/work-orders/${workOrderId}/assign`, {
    method: "POST",
    headers: authHeader(context),
    body: JSON.stringify({ employee_id: employeeId })
  });
  assertTenantScope(context, workOrder.tenant_id, "work_order");
  return workOrder;
}

export async function attachWorkOrderVehicle(
  context: WorkspaceContext,
  workOrderId: string,
  vehicleId: string
): Promise<WorkOrderRecord> {
  const workOrder = await backendRequest<WorkOrderRecord>(`/work-orders/${workOrderId}/attach-vehicle`, {
    method: "POST",
    headers: authHeader(context),
    body: JSON.stringify({ vehicle_id: vehicleId })
  });
  assertTenantScope(context, workOrder.tenant_id, "work_order");
  return workOrder;
}

export async function closeWorkOrder(context: WorkspaceContext, workOrderId: string): Promise<WorkOrderRecord> {
  const workOrder = await backendRequest<WorkOrderRecord>(`/work-orders/${workOrderId}/close`, {
    method: "POST",
    headers: authHeader(context)
  });
  assertTenantScope(context, workOrder.tenant_id, "work_order");
  return workOrder;
}

export async function listWorkOrderLines(context: WorkspaceContext, workOrderId: string): Promise<WorkOrderOrderLine[]> {
  const lines = await backendRequest<WorkOrderOrderLine[]>(`/work-orders/${workOrderId}/lines`, {
    method: "GET",
    headers: authHeader(context)
  });
  lines.forEach((line) => assertTenantScope(context, line.tenant_id, "order_line"));
  return lines;
}

export async function addWorkOrderLine(
  context: WorkspaceContext,
  workOrderId: string,
  payload: OrderLineCreatePayload
): Promise<WorkOrderOrderLine> {
  const line = await backendRequest<WorkOrderOrderLine>(`/work-orders/${workOrderId}/lines`, {
    method: "POST",
    headers: authHeader(context),
    body: JSON.stringify(payload)
  });
  assertTenantScope(context, line.tenant_id, "order_line");
  return line;
}

export async function patchWorkOrderLine(
  context: WorkspaceContext,
  workOrderId: string,
  lineId: string,
  payload: OrderLineUpdatePayload
): Promise<WorkOrderOrderLine> {
  const line = await backendRequest<WorkOrderOrderLine>(`/work-orders/${workOrderId}/lines/${lineId}`, {
    method: "PATCH",
    headers: authHeader(context),
    body: JSON.stringify(payload)
  });
  assertTenantScope(context, line.tenant_id, "order_line");
  return line;
}

export async function deleteWorkOrderLine(context: WorkspaceContext, workOrderId: string, lineId: string): Promise<void> {
  await backendRequest<void>(`/work-orders/${workOrderId}/lines/${lineId}`, {
    method: "DELETE",
    headers: authHeader(context)
  });
}

export async function listWorkOrderPayments(context: WorkspaceContext, workOrderId: string): Promise<PaymentRecord[]> {
  const payload = await backendRequest<PaymentRecord[]>(`/work-orders/${workOrderId}/payments`, {
    method: "GET",
    headers: authHeader(context)
  });
  payload.forEach((payment) => assertTenantScope(context, payment.tenant_id, "payment"));
  return payload;
}

export async function createWorkOrderPayment(
  context: WorkspaceContext,
  workOrderId: string,
  payload: PaymentCreatePayload
): Promise<PaymentRecord> {
  const payment = await backendRequest<PaymentRecord>(`/work-orders/${workOrderId}/payments`, {
    method: "POST",
    headers: authHeader(context),
    body: JSON.stringify(payload)
  });
  assertTenantScope(context, payment.tenant_id, "payment");
  return payment;
}
