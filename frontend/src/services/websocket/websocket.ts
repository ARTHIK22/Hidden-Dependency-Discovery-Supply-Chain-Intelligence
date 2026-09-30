import { WS_URL } from "../../config/env";

export function webSocketUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : "/" + path;
  return WS_URL + normalizedPath;
}

export function createWebSocket(
  path: string,
  protocols?: string | string[],
): WebSocket {
  const url = webSocketUrl(path);
  return protocols
    ? new WebSocket(url, protocols)
    : new WebSocket(url);
}
