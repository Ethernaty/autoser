export type ServerEnv = {
  BACKEND_API_URL: string;
};

const fallbackBackendApiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8001";

export const serverEnv: ServerEnv = {
  BACKEND_API_URL: process.env.BACKEND_API_URL ?? fallbackBackendApiUrl
};
