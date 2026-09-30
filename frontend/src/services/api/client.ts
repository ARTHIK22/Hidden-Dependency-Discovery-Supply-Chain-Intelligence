import { API_BASE_URL } from "../../config/api.config";
import { ApiError } from "./errors";
import { authHeaders, onUnauthorized } from "./interceptors";

type RequestOptions = Omit<RequestInit, "body"> & { body?: unknown; timeoutMs?: number };

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = 15000, body, headers, ...init } = options;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  const requestHeaders = authHeaders(headers);
  let requestBody: BodyInit | undefined;
  if (body !== undefined && body !== null) {
    if (body instanceof FormData || body instanceof Blob || typeof body === "string") requestBody = body;
    else {
      requestHeaders.set("Content-Type", "application/json");
      requestBody = JSON.stringify(body);
    }
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`, {
      ...init, body: requestBody, headers: requestHeaders, signal: controller.signal,
    });
    if (response.status === 401) onUnauthorized(path);
    if (!response.ok) {
      let message = response.statusText || "Request failed";
      let details: unknown;
      try {
        const payload = await response.json();
        details = payload.detail ?? payload;
        message = typeof details === "string" ? details : Array.isArray(details)
          ? details.map((issue) => issue.msg ?? JSON.stringify(issue)).join("; ")
          : payload.message ?? message;
      } catch { /* Keep the HTTP status message for non-JSON errors. */ }
      throw new ApiError(response.status, message, details);
    }
    if (response.status === 204) return undefined as T;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) return await response.json() as T;
    return await response.blob() as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") throw new Error("The request timed out. Please try again.");
    throw new Error("The backend is unavailable. Check your connection and try again.");
  } finally {
    window.clearTimeout(timer);
  }
}

function queryString(params: Record<string, string | number | boolean | null | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  const encoded = query.toString();
  return encoded ? `?${encoded}` : "";
}

export const apiClient = {
  get: <T>(path: string, params?: Record<string, string | number | boolean | null | undefined>) => request<T>(`${path}${params ? queryString(params) : ""}`, { method: "GET" }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
