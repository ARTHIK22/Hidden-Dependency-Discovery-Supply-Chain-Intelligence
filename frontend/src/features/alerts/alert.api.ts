import { apiClient } from "../../services/api/client";
import type { Alert } from "../../types/alert.types";
export const listAlerts = (params: { unread?: boolean; limit?: number } = {}) => apiClient.get<Alert[]>("/alerts", params);
export const markAlertRead = (id: string) => apiClient.post<Alert>(`/alerts/${encodeURIComponent(id)}/read`);
