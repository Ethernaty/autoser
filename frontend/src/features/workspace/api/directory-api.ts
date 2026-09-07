import { apiClient } from "@/shared/api/client";
import type { ClientRecord, PagedResponse } from "@/features/workspace/types/mvp-types";

export const CLIENT_SOURCES = ["Рекомендация", "Поиск в интернете", "Карты", "Социальные сети", "Реклама", "Вывеска", "Повторное обращение", "Другое"];
export type ClientDirectory = PagedResponse<ClientRecord> & { summary: { active_clients: number; with_vehicles: number; without_orders: number } };
export type ImportPreview = { rows: { row: number; data: { name: string; phone: string }; status: "ready" | "duplicate" | "invalid"; message: string; existing_client_id?: string }[]; created: number; ready: number; duplicates: number; invalid: number };
export async function fetchClientDirectory(params: { q: string; sort: string; activity: string; source: string; limit: number; offset: number }): Promise<ClientDirectory> {
  return (await apiClient.get<ClientDirectory>("/api/workspace/clients", { params })).data;
}
export async function importClientCsv(csv_text: string, commit: boolean): Promise<ImportPreview> {
  return (await apiClient.post<ImportPreview>("/api/workspace/clients/import", { csv_text, commit })).data;
}
