import { apiClient } from "../../services/api/client";
export const generateReport = (investigationId: string) => apiClient.post<Record<string, unknown>>(`/reports/investigations/${encodeURIComponent(investigationId)}`);
