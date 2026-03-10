import "server-only";

import { backendRequest } from "@/shared/api/backend-client";
import { WorkspaceScopeError } from "@/shared/errors/workspace-scope-error";
import type { AuthSession } from "@/features/auth/types/auth-types";
import type { WorkspaceContext } from "@/features/auth/api/backend-session";

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

export type OrderStatus = "new" | "in_progress" | "completed" | "canceled";

export type OrderRecord = {
  id: string;
  tenant_id: string;
  client_id: string;
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

export type ClientCardView = {
  query: string;
  selectedClient: ClientRecord | null;
  matches: ClientRecord[];
  historyOrders: WorkspaceOrderCard[];
};

const DEFAULT_LIST_LIMIT = 20;
const BACKEND_MAX_LIST_LIMIT = Number.parseInt(process.env.BACKEND_MAX_LIST_LIMIT ?? "50", 10);

function clampListLimit(limit: number | undefined): number {
  const fallback = DEFAULT_LIST_LIMIT;
  const normalized = Number.isFinite(limit) ? Number(limit) : fallback;
  const safeMax = Number.isFinite(BACKEND_MAX_LIST_LIMIT) && BACKEND_MAX_LIST_LIMIT > 0 ? BACKEND_MAX_LIST_LIMIT : 50;
  return Math.min(Math.max(1, Math.trunc(normalized)), safeMax);
}

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

function assertWorkspaceScope(context: WorkspaceContext, tenantId: string | null | undefined, entity: string): void {
  if (!tenantId || tenantId !== context.workspaceId) {
    throw new WorkspaceScopeError({
      expectedWorkspaceId: context.workspaceId,
      actualWorkspaceId: tenantId ?? null,
      entity
    });
  }
}

function ensureScopedRecord<T extends { tenant_id: string }>(
  context: WorkspaceContext,
  record: T,
  entity: string
): T {
  assertWorkspaceScope(context, record.tenant_id, entity);
  return record;
}

function ensureScopedPage<T extends { tenant_id: string }>(
  context: WorkspaceContext,
  page: PagedResponse<T>,
  entity: string
): PagedResponse<T> {
  page.items.forEach((item) => {
    assertWorkspaceScope(context, item.tenant_id, entity);
  });

  return page;
}

function toIsoLocalLabel(value: string): string {
  const date = new Date(value);
  return date.toLocaleString();
}

function isOverdue(createdAt: string, status: OrderStatus): boolean {
  if (status !== "new") {
    return false;
  }
  const created = new Date(createdAt).getTime();
  return Date.now() - created > 3 * 60 * 60 * 1000;
}

export async function getSessionFromBackend(context: WorkspaceContext): Promise<AuthSession> {
  const session = await backendRequest<AuthSession>("/auth/me", {
    method: "GET",
    headers: authHeader(context)
  });

  if (session.workspaceId !== context.workspaceId) {
    throw new WorkspaceScopeError({
      expectedWorkspaceId: context.workspaceId,
      actualWorkspaceId: session.workspaceId,
      entity: "auth_session"
    });
  }

  return session;
}

export async function listClients(
  context: WorkspaceContext,
  params: {
    q?: string;
    limit?: number;
    offset?: number;
  }
): Promise<PagedResponse<ClientRecord>> {
  const query = new URLSearchParams();
  if (params.q) {
    query.set("q", params.q);
  }
  query.set("limit", String(clampListLimit(params.limit)));
  query.set("offset", String(params.offset ?? 0));

  const page = await backendRequest<PagedResponse<ClientRecord>>(`/clients/?${query.toString()}`, {
    method: "GET",
    headers: authHeader(context)
  });

  return ensureScopedPage(context, page, "client_list");
}

export async function listClientsByIds(context: WorkspaceContext, ids: string[]): Promise<ClientRecord[]> {
  if (!ids.length) {
    return [];
  }

  const payload = await backendRequest<ClientRecord[]>("/clients/batch", {
    method: "POST",
    headers: authHeader(context),
    body: JSON.stringify({ ids })
  });

  return payload.map((record) => ensureScopedRecord(context, record, "client"));
}

export async function getClient(context: WorkspaceContext, clientId: string): Promise<ClientRecord> {
  const record = await backendRequest<ClientRecord>(`/clients/${clientId}`, {
    method: "GET",
    headers: authHeader(context)
  });

  return ensureScopedRecord(context, record, "client");
}

export async function createClient(
  context: WorkspaceContext,
  payload: {
    name: string;
    phone: string;
    email?: string | null;
    comment?: string | null;
  },
  options?: { idempotencyKey?: string }
): Promise<ClientRecord> {
  const headers = authHeader(context);
  if (options?.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }

  const record = await backendRequest<ClientRecord>("/clients/", {
    method: "POST",
    headers,
    body: JSON.stringify(payload)
  });

  return ensureScopedRecord(context, record, "client");
}

export async function updateClient(
  context: WorkspaceContext,
  clientId: string,
  payload: {
    name?: string;
    phone?: string;
    email?: string | null;
    comment?: string | null;
    version?: number;
  }
): Promise<ClientRecord> {
  const record = await backendRequest<ClientRecord>(`/clients/${clientId}`, {
    method: "PATCH",
    headers: authHeader(context),
    body: JSON.stringify(payload)
  });

  return ensureScopedRecord(context, record, "client");
}

export async function listOrders(
  context: WorkspaceContext,
  params: {
    q?: string;
    limit?: number;
    offset?: number;
  }
): Promise<PagedResponse<OrderRecord>> {
  const query = new URLSearchParams();
  if (params.q) {
    query.set("q", params.q);
  }
  query.set("limit", String(clampListLimit(params.limit)));
  query.set("offset", String(params.offset ?? 0));

  const page = await backendRequest<PagedResponse<OrderRecord>>(`/orders/?${query.toString()}`, {
    method: "GET",
    headers: authHeader(context)
  });

  return ensureScopedPage(context, page, "order_list");
}

export async function createOrder(
  context: WorkspaceContext,
  payload: {
    client_id: string;
    description: string;
    price: number;
    status?: OrderStatus;
  },
  options?: { idempotencyKey?: string }
): Promise<OrderRecord> {
  const headers = authHeader(context);
  if (options?.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }

  const record = await backendRequest<OrderRecord>("/orders/", {
    method: "POST",
    headers,
    body: JSON.stringify({
      ...payload,
      status: payload.status ?? "new"
    })
  });

  return ensureScopedRecord(context, record, "order");
}

export async function updateOrderStatus(
  context: WorkspaceContext,
  orderId: string,
  status: OrderStatus
): Promise<OrderRecord> {
  const record = await backendRequest<OrderRecord>(`/orders/${orderId}`, {
    method: "PATCH",
    headers: authHeader(context),
    body: JSON.stringify({ status })
  });

  return ensureScopedRecord(context, record, "order");
}

export async function updateOrder(
  context: WorkspaceContext,
  orderId: string,
  payload: {
    description?: string;
    price?: number;
    status?: OrderStatus;
  }
): Promise<OrderRecord> {
  const record = await backendRequest<OrderRecord>(`/orders/${orderId}`, {
    method: "PATCH",
    headers: authHeader(context),
    body: JSON.stringify(payload)
  });

  return ensureScopedRecord(context, record, "order");
}

async function resolveClientMap(context: WorkspaceContext, orders: OrderRecord[]): Promise<Map<string, string>> {
  const ids = Array.from(new Set(orders.map((item) => item.client_id)));
  if (!ids.length) {
    return new Map();
  }

  const chunkSize = 100;
  const chunks: string[][] = [];
  for (let index = 0; index < ids.length; index += chunkSize) {
    chunks.push(ids.slice(index, index + chunkSize));
  }

  const results = await Promise.all(
    chunks.map(async (chunk) => {
      try {
        return await listClientsByIds(context, chunk);
      } catch {
        return [];
      }
    })
  );

  const map = new Map<string, string>();
  results.flat().forEach((client) => {
    map.set(client.id, client.name);
  });

  ids.forEach((id) => {
    if (!map.has(id)) {
      map.set(id, "Unknown client");
    }
  });

  return map;
}

function toOrderCards(orders: OrderRecord[], clientMap: Map<string, string>): WorkspaceOrderCard[] {
  return orders
    .map((order) => ({
      id: order.id,
      clientId: order.client_id,
      clientName: clientMap.get(order.client_id) ?? "Unknown client",
      description: order.description,
      price: order.price,
      status: order.status,
      createdAt: order.created_at,
      overdue: isOverdue(order.created_at, order.status)
    }))
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
}

export async function buildDashboardView(context: WorkspaceContext): Promise<DashboardView> {
  const ordersResponse = await listOrders(context, { limit: 80, offset: 0 });
  const clientMap = await resolveClientMap(context, ordersResponse.items);
  const cards = toOrderCards(ordersResponse.items, clientMap);

  const now = new Date();
  const nowTs = now.getTime();
  const threeDaysMs = 3 * 24 * 60 * 60 * 1000;

  return {
    nowLabel: toIsoLocalLabel(now.toISOString()),
    inProgressCount: cards.filter((item) => item.status === "in_progress").length,
    waitingCount: cards.filter((item) => item.status === "new").length,
    readyCount: cards.filter((item) => item.status === "completed").length,
    cashCount: cards.filter((item) => item.status === "completed" && nowTs - new Date(item.createdAt).getTime() <= threeDaysMs)
      .length,
    recentOrders: cards.slice(0, 8)
  };
}

export async function buildTodayView(context: WorkspaceContext): Promise<TodayView> {
  const ordersResponse = await listOrders(context, { limit: 120, offset: 0 });
  const clientMap = await resolveClientMap(context, ordersResponse.items);
  const cards = toOrderCards(ordersResponse.items, clientMap);

  const inProgress = cards.filter((item) => item.status === "in_progress").slice(0, 12);
  const waiting = cards.filter((item) => item.status === "new").slice(0, 12);
  const overdue = waiting.filter((item) => item.overdue).slice(0, 12);
  const ready = cards.filter((item) => item.status === "completed").slice(0, 12);

  return {
    nowLabel: toIsoLocalLabel(new Date().toISOString()),
    inProgress,
    waiting,
    overdue,
    ready
  };
}

export async function buildCashDeskView(context: WorkspaceContext): Promise<CashDeskView> {
  const ordersResponse = await listOrders(context, { limit: 120, offset: 0 });
  const clientMap = await resolveClientMap(context, ordersResponse.items);
  const cards = toOrderCards(ordersResponse.items, clientMap);

  const rows = cards.filter((item) => item.status === "completed").slice(0, 20);
  const totalDue = rows.reduce((acc, row) => acc + Number(row.price), 0).toFixed(2);

  return {
    nowLabel: toIsoLocalLabel(new Date().toISOString()),
    totalDue,
    rows
  };
}

export async function buildClientCardView(
  context: WorkspaceContext,
  params: {
    q?: string;
    clientId?: string;
  }
): Promise<ClientCardView> {
  const query = params.q?.trim() ?? "";
  const matches = query ? (await listClients(context, { q: query, limit: 8, offset: 0 })).items : [];

  let selectedClient: ClientRecord | null = null;
  if (params.clientId) {
    try {
      selectedClient = await getClient(context, params.clientId);
    } catch {
      selectedClient = matches[0] ?? null;
    }
  } else {
    selectedClient = matches[0] ?? null;
  }

  let historyOrders: WorkspaceOrderCard[] = [];
  if (selectedClient) {
    const ordersResponse = await listOrders(context, { limit: 200, offset: 0 });
    const filtered = ordersResponse.items.filter((item) => item.client_id === selectedClient!.id);
    const clientMap = new Map([[selectedClient.id, selectedClient.name]]);
    historyOrders = toOrderCards(filtered, clientMap).slice(0, 12);
  }

  return {
    query,
    selectedClient,
    matches,
    historyOrders
  };
}

export async function createOrderFromWorkflow(
  context: WorkspaceContext,
  payload: {
    phone: string;
    clientName?: string;
    description: string;
    price: number;
    selectedClientId?: string;
  },
  options?: { idempotencyKey?: string }
): Promise<{ orderId: string }> {
  const phone = payload.phone.trim();
  const description = payload.description.trim();

  if (!phone) {
    throw new Error("Phone is required");
  }
  if (!description) {
    throw new Error("Description is required");
  }
  if (!Number.isFinite(payload.price) || payload.price <= 0) {
    throw new Error("Invalid price");
  }

  let clientId = payload.selectedClientId;

  if (!clientId) {
    const existing = await listClients(context, { q: phone, limit: 1, offset: 0 });
    if (existing.items.length) {
      clientId = existing.items[0].id;
    } else {
      const fallbackName = payload.clientName?.trim() || `Client ${phone.slice(-4)}`;
      const client = await createClient(context, {
        name: fallbackName,
        phone,
        comment: "Created from quick order"
      });
      clientId = client.id;
    }
  }

  const order = await createOrder(context, {
    client_id: clientId,
    description,
    price: payload.price,
    status: "new"
  }, options);

  return { orderId: order.id };
}

