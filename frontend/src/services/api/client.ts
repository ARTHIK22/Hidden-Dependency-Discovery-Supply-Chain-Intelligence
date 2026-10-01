import { API_BASE_URL } from "../../config/env";
import { authHeaders, onUnauthorized } from "./interceptors";

export class ApiError extends Error {
  readonly status: number;
  readonly payload: unknown;
  readonly details: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
    this.details = payload;
  }
}

export type ApiQueryValue = string | number | boolean | null | undefined;
export type ApiParams = Readonly<Record<string, ApiQueryValue>>;
export type ApiRequestOptions = {
  params?: ApiParams;
  signal?: AbortSignal;
  headers?: HeadersInit;
};

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = authHeaders(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("Accept", "application/json");

  let response: Response;
  try {
    response = await fetch(apiUrl(path), { ...init, headers });
  } catch (error) {
    throw new ApiError(
      error instanceof Error ? error.message : "The API could not be reached.",
      0,
      error,
    );
  }

  if (response.status === 204) return undefined as T;

  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json") || contentType.includes("+json")
    ? await response.json().catch(() => null)
    : await response.text().catch(() => "");

  if (!response.ok) {
    if (response.status === 401) onUnauthorized(path);
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? (payload as { detail?: unknown }).detail
        : undefined;
    const message =
      typeof detail === "string"
        ? detail
        : typeof payload === "string" && payload
          ? payload
          : `Request failed (${response.status}).`;
    throw new ApiError(message, response.status, payload);
  }

  return payload as T;
}

export const get = <T>(path: string, signal?: AbortSignal) =>
  request<T>(path, { method: "GET", signal });

export const post = <T>(path: string, body?: unknown) =>
  request<T>(path, {
    method: "POST",
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });

export const patch = <T>(path: string, body?: unknown) =>
  request<T>(path, {
    method: "PATCH",
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });

export const remove = <T = void>(path: string) =>
  request<T>(path, { method: "DELETE" });

function withParams(path: string, params?: ApiParams): string {
  if (!params) return path;
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const encoded = search.toString();
  if (!encoded) return path;
  return `${path}${path.includes("?") ? "&" : "?"}${encoded}`;
}

function isAbortSignal(value: unknown): value is AbortSignal {
  return typeof value === "object" && value !== null &&
    "aborted" in value && "addEventListener" in value;
}

function getOptions(
  value?: ApiParams | ApiRequestOptions | AbortSignal,
  config?: ApiRequestOptions,
): ApiRequestOptions {
  if (config) {
    return {
      ...config,
      params: value && !isAbortSignal(value) && !("params" in value) && !("signal" in value) && !("headers" in value)
        ? value as ApiParams
        : config.params,
    };
  }
  if (!value) return {};
  if (isAbortSignal(value)) return { signal: value };
  if ("params" in value || "signal" in value || "headers" in value) {
    return value as ApiRequestOptions;
  }
  return { params: value as ApiParams };
}

function send<T>(method: string, path: string, body?: unknown, options: ApiRequestOptions = {}) {
  return request<T>(withParams(path, options.params), {
    method,
    signal: options.signal,
    headers: options.headers,
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

// Feature APIs use this shared fetch client so URL, query, JSON and error handling
// stay consistent across the application.
export const apiClient = {
  get<T>(path: string, paramsOrOptions?: ApiParams | ApiRequestOptions | AbortSignal, config?: ApiRequestOptions) {
    return send<T>("GET", path, undefined, getOptions(paramsOrOptions, config));
  },
  post<T>(path: string, body?: unknown, options?: ApiRequestOptions) {
    return send<T>("POST", path, body, options);
  },
  put<T>(path: string, body?: unknown, options?: ApiRequestOptions) {
    return send<T>("PUT", path, body, options);
  },
  patch<T>(path: string, body?: unknown, options?: ApiRequestOptions) {
    return send<T>("PATCH", path, body, options);
  },
  delete<T = void>(path: string, options?: ApiRequestOptions) {
    return send<T>("DELETE", path, undefined, options);
  },
};

export function queryString(values: Record<string, string | number | boolean | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

// Retained for existing callers that need to inspect a raw Response.
export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers = authHeaders(init?.headers);
  headers.set("Accept", "application/json");
  return fetch(apiUrl(path), { ...init, headers }).then((response) => {
    if (response.status === 401) onUnauthorized(path);
    return response;
  });
}
