export type WorkOrderStatus = "new" | "in_progress" | "completed_unpaid" | "completed_paid" | "cancelled";
export type PaymentMethod = "cash" | "card" | "transfer" | "other";
export type OrderLineType = "labor" | "part" | "misc";
export type WorkOrderPaymentState = "unpaid" | "partial" | "paid";

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

export type AnalyticsMonthlyLoadItem = {
  period: string;
  orders_count: number;
  clients_count: number;
};

export type AnalyticsWeekdayLoadItem = {
  weekday: string;
  orders_count: number;
};

export type AnalyticsRevenueItem = {
  period: string;
  paid_amount: string;
  order_amount: string;
};

export type AnalyticsClientSourceItem = {
  source: string;
  clients_count: number;
};

export type AnalyticsPopularServiceItem = {
  name: string;
  usage_count: number;
};

export type AnalyticsProblemOrderItem = {
  id: string;
  description: string;
  status: string;
  remaining_amount: string;
  created_at: string;
};

export type DashboardAnalytics = {
  generated_at: string;
  clients_total: number;
  work_orders_total: number;
  open_work_orders_count: number;
  closed_work_orders_count: number;
  paid_amount_30d: string;
  unpaid_orders_count: number;
  seasonality_monthly: AnalyticsMonthlyLoadItem[];
  load_by_weekday: AnalyticsWeekdayLoadItem[];
  revenue_monthly: AnalyticsRevenueItem[];
  client_sources: AnalyticsClientSourceItem[];
  popular_services: AnalyticsPopularServiceItem[];
  problematic_orders: AnalyticsProblemOrderItem[];
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
  source: string | null;
  comment: string | null;
  version: number;
  created_at: string;
  updated_at: string;
};

export type ClientCreatePayload = {
  name: string;
  phone: string;
  email?: string | null;
  source?: string | null;
  comment?: string | null;
};

export type ClientUpdatePayload = {
  name?: string;
  phone?: string;
  email?: string | null;
  source?: string | null;
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
  full_name: string | null;
  email: string;
  role: string;
  is_active: boolean;
  version: number;
  created_at: string;
};

export type EmployeeCreatePayload = {
  full_name: string;
  email?: string | null;
  password: string;
  role: string;
};

export type EmployeeUpdatePayload = {
  full_name?: string;
  email?: string;
  password?: string;
  role?: string;
  is_active?: boolean;
};

export type WorkOrderRecord = {
  id: string;
  tenant_id: string;
  client_id: string;
  client_name?: string | null;
  vehicle_id: string | null;
  vehicle_plate_number?: string | null;
  vehicle_make_model?: string | null;
  assigned_employee_id: string | null;
  assigned_user_id: string | null;
  description: string;
  total_amount: string;
  price: string;
  status: WorkOrderStatus;
  payment_state: WorkOrderPaymentState;
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

export type WorkOrderTimelineEvent = {
  id: string;
  work_order_id: string;
  action: string;
  message: string;
  user_id: string;
  actor_email: string | null;
  actor_role: string | null;
  created_at: string;
};

export type WorkOrderHistoryItem = {
  id: string;
  client_id: string;
  client_name: string | null;
  vehicle_id: string | null;
  vehicle_plate_number: string | null;
  vehicle_make_model: string | null;
  description: string;
  work_summary: string | null;
  status: WorkOrderStatus;
  total_amount: string;
  paid_amount: string;
  remaining_amount: string;
  visit_at: string;
  created_at: string;
  updated_at: string;
};

export type SupportTicketCategory = "general" | "bug" | "payment" | "data" | "access" | "other";
export type SupportTicketStatus = "open" | "in_progress" | "resolved" | "closed";

export type SupportTicketRecord = {
  id: string;
  tenant_id: string;
  reporter_user_id: string;
  subject: string;
  category: SupportTicketCategory;
  message: string;
  status: SupportTicketStatus;
  created_at: string;
  updated_at: string;
};

export type SupportTicketListResponse = PagedResponse<SupportTicketRecord>;

export type SupportTicketCreatePayload = {
  subject: string;
  category: SupportTicketCategory;
  message: string;
};
