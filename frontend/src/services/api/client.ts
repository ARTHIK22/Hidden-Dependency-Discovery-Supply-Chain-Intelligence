import { API_BASE_URL } from "../../config/env";

export class ApiError extends Error {
  readonly status: number;
  readonly payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
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
  const payload: unknown = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : await response.text().catch(() => "");

  if (!response.ok) {
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
  return fetch(apiUrl(path), init);
}
