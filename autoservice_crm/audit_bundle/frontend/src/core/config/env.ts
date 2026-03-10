export type Env = {
  NEXT_PUBLIC_API_URL: string;
  NEXT_PUBLIC_APP_NAME: string;
  NEXT_PUBLIC_API_BASE_URL: string;
};

const fallbackEnv: Env = {
  NEXT_PUBLIC_API_URL: "http://127.0.0.1:8001",
  NEXT_PUBLIC_APP_NAME: "AutoService SaaS",
  NEXT_PUBLIC_API_BASE_URL: ""
};

export const env: Env = {
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? fallbackEnv.NEXT_PUBLIC_API_URL,
  NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME ?? fallbackEnv.NEXT_PUBLIC_APP_NAME,
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? fallbackEnv.NEXT_PUBLIC_API_BASE_URL
};
