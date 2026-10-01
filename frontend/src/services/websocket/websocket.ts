import { WS_URL } from "../../config/env";
import { tokenStorage } from "../storage/localStorage";

export function webSocketUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : "/" + path;
  return WS_URL + normalizedPath;
}

export function createWebSocket(
  path: string,
  protocols?: string | string[],
): WebSocket {
  const url = webSocketUrl(path);
  const requested = protocols ? (Array.isArray(protocols) ? protocols : [protocols]) : [];
  const token = tokenStorage.get();
  const authenticated = token
    ? [...requested, "hdi", `bearer.${token}`]
    : requested;
  return authenticated.length
    ? new WebSocket(url, [...new Set(authenticated)])
    : new WebSocket(url);
}
