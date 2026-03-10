export type AuditRecord = {
  id: string;
  userId: string;
  workspaceId: string;
  entity: string;
  entityId: string | null;
  action: string;
  previousValue: Record<string, unknown> | null;
  newValue: Record<string, unknown> | null;
  metadata: Record<string, unknown>;
  timestamp: string;
};

export type AuditPage = {
  items: AuditRecord[];
  limit: number;
  offset: number;
  hasNext: boolean;
};

export type AuditListParams = {
  limit?: number;
  offset?: number;
  q?: string;
  level?: string;
};

export type CreateAuditEventPayload = {
  entity: string;
  entityId?: string;
  action: string;
  previousValue?: Record<string, unknown> | null;
  newValue?: Record<string, unknown> | null;
  metadata?: Record<string, unknown>;
};

