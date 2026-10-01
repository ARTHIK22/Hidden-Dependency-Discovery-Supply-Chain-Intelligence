import { get, post, queryString } from "../../services/api/client";
import type { ApiList, Risk } from "../../types/api.types";

export const listRisks = (level?: string, signal?: AbortSignal) =>
  get<ApiList<Risk>>(`/risks${queryString({ level, limit: 250 })}`, signal);

export const getRiskSummary = (signal?: AbortSignal) =>
  get<{ total: number; high_risk: number; average_score: number; unknown?: number }>("/risks/summary", signal);

export type RiskAnalysisState = {
  investigation_id: string;
  status: string;
  progress: number;
  risk_progress: Record<string, unknown> | null;
  risk_analysis: Record<string, unknown> | null;
  error_message: string | null;
};

export const analyzeRisk = (investigationId: string) =>
  post<RiskAnalysisState>(`/investigations/${encodeURIComponent(investigationId)}/analyze-risk`);

export const getRiskAnalysisState = (investigationId: string, signal?: AbortSignal) =>
  get<RiskAnalysisState>(`/investigations/${encodeURIComponent(investigationId)}/risk-analysis`, signal);

export const getInvestigationRisks = (investigationId: string, signal?: AbortSignal) =>
  get<ApiList<Risk>>(`/investigations/${encodeURIComponent(investigationId)}/risks?limit=250`, signal);

export const getInvestigationRiskSummary = (investigationId: string, signal?: AbortSignal) =>
  get<Record<string, unknown>>(`/investigations/${encodeURIComponent(investigationId)}/risk-summary`, signal);
