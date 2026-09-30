import { get, patch, queryString, remove } from "../../services/api/client";
import type { Alert, ApiList } from "../../types/api.types";

export const listAlerts = (unreadOnly = false, signal?: AbortSignal) =>
  get<ApiList<Alert>>(`/alerts${queryString({ unread_only: unreadOnly, limit: 250 })}`, signal);

export const markAlertRead = (id: string) =>
  patch<Alert>(`/alerts/${encodeURIComponent(id)}/read`);

export const dismissAlert = (id: string) =>
  remove(`/alerts/${encodeURIComponent(id)}`);
