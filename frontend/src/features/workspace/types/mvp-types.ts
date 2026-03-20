export type WorkOrderStatus = "new" | "in_progress" | "completed" | "canceled";
export type PaymentMethod = "cash" | "card" | "transfer" | "other";
export type OrderLineType = "labor" | "part" | "misc";

export type PagedResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type DashboardActivity = {
  id: string;
  entity: string;
  entity_id: string | null;
  action: string;
  user_id: string;
  created_at: string;
};

export type DashboardSummary = {
  open_work_orders_count: number;
  closed_work_orders_count: number;
  revenue_total: string;
  recent_activity: DashboardActivity[];
};

export type WorkspaceContextResponse = {
  workspace_id: string;
  workspace_slug: string;
  workspace_name: string;
  role: string;
  user_id: string;
};

export type WorkspaceSettingsResponse = {
  id: string;
  tenant_id: string;
  service_name: string;
  phone: string;
  address: string | null;
  timezone: string;
  currency: string;
  working_hours_note: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkspaceSettingsUpdatePayload = {
  service_name?: string;
  phone?: string;
  address?: string | null;
  timezone?: string;
  currency?: string;
  working_hours_note?: string | null;
};

export type ClientRecord = {
  id: string;
  tenant_id: string;
  name: string;
  phone: string;
  email: string | null;
  comment: string | null;
  version: number;
  created_at: string;
  updated_at: string;
};

export type ClientCreatePayload = {
  name: string;
  phone: string;
  email?: string | null;
  comment?: string | null;
};

export type ClientUpdatePayload = {
  name?: string;
  phone?: string;
  email?: string | null;
  comment?: string | null;
  version?: number;
};

export type VehicleRecord = {
  id: string;
  tenant_id: string;
  client_id: string;
  plate_number: string;
  make_model: string;
  year: number | null;
  vin: string | null;
  comment: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type VehicleCreatePayload = {
  client_id: string;
  plate_number: string;
  make_model: string;
  year?: number | null;
  vin?: string | null;
  comment?: string | null;
};

export type VehicleUpdatePayload = {
  plate_number?: string;
  make_model?: string;
  year?: number | null;
  vin?: string | null;
  comment?: string | null;
  archived?: boolean;
};

export type EmployeeRecord = {
  employee_id: string;
  user_id: string;
  tenant_id: string;
  email: string;
  role: string;
  is_active: boolean;
  version: number;
  created_at: string;
};

export type EmployeeCreatePayload = {
  email: string;
  password: string;
  role: string;
};

export type EmployeeUpdatePayload = {
  email?: string;
  password?: string;
  role?: string;
  is_active?: boolean;
};

export type WorkOrderRecord = {
  id: string;
  tenant_id: string;
  client_id: string;
  vehicle_id: string | null;
  assigned_employee_id: string | null;
  assigned_user_id: string | null;
  description: string;
  total_amount: string;
  price: string;
  status: WorkOrderStatus;
  paid_amount: string;
  remaining_amount: string;
  created_at: string;
  updated_at: string;
};

export type WorkOrderCreatePayload = {
  client_id: string;
  vehicle_id: string;
  description: string;
  total_amount: number;
  status?: WorkOrderStatus;
  assigned_employee_id?: string | null;
};

export type WorkOrderUpdatePayload = {
  description?: string;
  total_amount?: number;
  status?: WorkOrderStatus;
  vehicle_id?: string;
  assigned_employee_id?: string | null;
};

export type WorkOrderOrderLine = {
  id: string;
  tenant_id: string;
  order_id: string;
  line_type: OrderLineType;
  name: string;
  quantity: string;
  unit_price: string;
  line_total: string;
  position: number;
  comment: string | null;
  created_at: string;
  updated_at: string;
};

export type OrderLineCreatePayload = {
  line_type: OrderLineType;
  name: string;
  quantity: number;
  unit_price: number;
  position?: number;
  comment?: string | null;
};

export type OrderLineUpdatePayload = {
  line_type?: OrderLineType;
  name?: string;
  quantity?: number;
  unit_price?: number;
  position?: number;
  comment?: string | null;
};

export type PaymentRecord = {
  id: string;
  tenant_id: string;
  order_id: string;
  created_by_user_id: string;
  amount: string;
  method: PaymentMethod;
  paid_at: string;
  comment: string | null;
  external_ref: string | null;
  voided_at: string | null;
  created_at: string;
};

export type PaymentCreatePayload = {
  amount: number;
  method: PaymentMethod;
  paid_at?: string;
  comment?: string | null;
  external_ref?: string | null;
};
