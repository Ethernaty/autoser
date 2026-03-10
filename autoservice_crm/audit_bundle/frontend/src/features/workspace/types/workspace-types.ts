export type OrderStatus = "new" | "in_progress" | "completed" | "canceled";

export type WorkspaceOrderCard = {
  id: string;
  clientId: string;
  clientName: string;
  description: string;
  price: string;
  status: OrderStatus;
  createdAt: string;
  overdue: boolean;
};

export type DashboardView = {
  nowLabel: string;
  inProgressCount: number;
  waitingCount: number;
  readyCount: number;
  cashCount: number;
  recentOrders: WorkspaceOrderCard[];
};

export type TodayView = {
  nowLabel: string;
  inProgress: WorkspaceOrderCard[];
  waiting: WorkspaceOrderCard[];
  overdue: WorkspaceOrderCard[];
  ready: WorkspaceOrderCard[];
};

export type CashDeskView = {
  nowLabel: string;
  totalDue: string;
  rows: WorkspaceOrderCard[];
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

export type OrderRecord = {
  id: string;
  tenant_id: string;
  client_id: string;
  client_name?: string;
  description: string;
  price: string;
  status: OrderStatus;
  created_at: string;
  updated_at: string;
};

export type PagedResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type ClientCardView = {
  query: string;
  selectedClient: ClientRecord | null;
  matches: ClientRecord[];
  historyOrders: WorkspaceOrderCard[];
};

export type CreateWorkflowOrderPayload = {
  phone: string;
  clientName?: string;
  description: string;
  price: number;
  selectedClientId?: string;
};

export type CreateClientPayload = {
  name: string;
  phone: string;
  email?: string | null;
  comment?: string | null;
};

export type UpdateClientPayload = {
  clientId: string;
  name?: string;
  phone?: string;
  email?: string | null;
  comment?: string | null;
};

export type UpdateOrderPayload = {
  orderId: string;
  description?: string;
  price?: number;
  status?: OrderStatus;
};

export type WorkspaceListParams = {
  q?: string;
  limit?: number;
  offset?: number;
};
