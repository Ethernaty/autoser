import { apiClient } from "@/shared/api/client";

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export type RequestOptions<TBody = unknown> = {
  method?: HttpMethod;
  body?: TBody;
  headers?: Record<string, string>;
  signal?: AbortSignal;
};

export async function request<TResponse, TBody = unknown>(
  path: string,
  options: RequestOptions<TBody> = {}
): Promise<TResponse> {
  const response = await apiClient.request<TResponse>({
    url: path,
    method: options.method ?? "GET",
    data: options.body,
    headers: options.headers,
    signal: options.signal
  });

  return response.data;
}
