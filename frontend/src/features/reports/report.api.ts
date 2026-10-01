import { apiClient, apiFetch } from "../../services/api/client";
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

export const downloadReport = async (id: string, format: "json" | "csv" | "txt" = "txt"): Promise<Blob> => {
  const response = await apiFetch(`/reports/${encodeURIComponent(id)}/export?format=${format}`);
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const detail = typeof payload === "object" && payload !== null && "detail" in payload
      ? (payload as { detail?: unknown }).detail
      : null;
    throw new Error(typeof detail === "string" ? detail : `Report export failed (${response.status}).`);
  }
  return response.blob();
};
