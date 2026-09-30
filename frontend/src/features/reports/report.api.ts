import { apiClient } from "../../services/api/client";
import type { ApiList, Report } from "../../types/api.types";

export const listReports = (investigationId?: string, signal?: AbortSignal) =>
  apiClient.get<ApiList<Report>>("/reports", {
    params: { investigation_id: investigationId, limit: 250 },
    signal,
  });

export const generateReport = (investigationId: string) =>
  apiClient.post<Report>("/reports", { investigation_id: investigationId });

export const getReport = (id: string, signal?: AbortSignal) =>
  apiClient.get<Report>(`/reports/${encodeURIComponent(id)}`, { signal });

export const downloadReport = (id: string) =>
  apiClient.get<string>(`/reports/${encodeURIComponent(id)}/download`);
