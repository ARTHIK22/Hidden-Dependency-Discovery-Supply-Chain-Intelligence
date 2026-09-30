import { tokenStorage } from "../storage/localStorage";

export function authHeaders(headers: HeadersInit = {}): Headers {
  const result = new Headers(headers);
  const token = tokenStorage.get();
  if (token) result.set("Authorization", `Bearer ${token}`);
  return result;
}

export function onUnauthorized(path: string): void {
  tokenStorage.clear();
  if (path.includes("/auth/login") || path.includes("/auth/register")) return;
  window.dispatchEvent(new CustomEvent("hdi:unauthorized"));
}
