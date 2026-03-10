"use client";

import axios, { AxiosError, type AxiosRequestConfig } from "axios";

import { env } from "@/core/config/env";
import { emitUnauthorized } from "@/shared/api/events";

export type ApiErrorPayload = {
  detail?: string;
  code?: string;
  message?: string;
  details?: unknown;
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
};

export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor({ message, status, code, details }: { message: string; status: number; code: string; details?: unknown }) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

declare module "axios" {
  export interface AxiosRequestConfig {
    skipAuthHandling?: boolean;
  }
}

function normalizeAxiosError(error: unknown): ApiClientError {
  if (!axios.isAxiosError(error)) {
    return new ApiClientError({
      message: "Unexpected network error",
      status: 500,
      code: "unexpected_error"
    });
  }

  const axiosError = error as AxiosError<ApiErrorPayload>;
  const status = axiosError.response?.status ?? 500;
  const payload = axiosError.response?.data;

  const message =
    payload?.error?.message ??
    payload?.message ??
    payload?.detail ??
    axiosError.message ??
    "Request failed";

  const code = payload?.error?.code ?? payload?.code ?? `http_${status}`;
  const details = payload?.error?.details ?? payload?.details;

  return new ApiClientError({
    message,
    status,
    code,
    details
  });
}

export function isApiClientError(error: unknown): error is ApiClientError {
  return error instanceof ApiClientError;
}

export const apiClient = axios.create({
  baseURL: env.NEXT_PUBLIC_API_BASE_URL,
  withCredentials: true,
  timeout: 20_000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
    "X-Requested-With": "XMLHttpRequest"
  }
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const normalized = normalizeAxiosError(error);
    const config = (error as AxiosError).config as AxiosRequestConfig | undefined;

    if (normalized.status === 401 && !config?.skipAuthHandling) {
      emitUnauthorized();
    }

    return Promise.reject(normalized);
  }
);
