import { get, post, queryString } from "../../services/api/client";
import type { ApiList, Report } from "../../types/api.types";

export const listReports = (investigationId?: string, signal?: AbortSignal) =>
  get<ApiList<Report>>(`/reports${queryString({ investigation_id: investigationId, limit: 250 })}`, signal);

export const generateReport = (investigation_id: string) =>
  post<Report>("/reports", { investigation_id });

export const getReport = (id: string, signal?: AbortSignal) =>
  get<Report>(`/reports/${encodeURIComponent(id)}`, signal);

export const downloadReport = (id: string) =>
  get<string>(`/reports/${encodeURIComponent(id)}/download`);
