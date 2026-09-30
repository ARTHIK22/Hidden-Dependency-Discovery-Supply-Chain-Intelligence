const normalizeBaseUrl = (value: string | undefined, fallback: string): string =>
  (value?.trim() || fallback).replace(/\/+$/, "");

export const API_BASE_URL = normalizeBaseUrl(
  import.meta.env.VITE_API_BASE_URL,
  "http://localhost:8000/api",
);

export const WS_URL = normalizeBaseUrl(
  import.meta.env.VITE_WS_URL,
  "ws://localhost:8000/ws",
);

export const APP_NAME =
  import.meta.env.VITE_APP_NAME?.trim() || "Hidden Dependency Discovery";

export const APP_ENV =
  import.meta.env.VITE_APP_ENV?.trim() || "development";

export const env = Object.freeze({
  apiBaseUrl: API_BASE_URL,
  wsUrl: WS_URL,
  appName: APP_NAME,
  environment: APP_ENV,
});
