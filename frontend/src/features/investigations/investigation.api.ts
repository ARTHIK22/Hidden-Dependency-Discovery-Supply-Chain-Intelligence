import { get, post, queryString, remove } from "../../services/api/client";
import type {
  ApiList,
  Investigation,
  InvestigationCreate,
  InvestigationCreateResponse,
  InvestigationDetail,
  InvestigationPlan,
  ResearchState,
  VerificationProgress,
  InvestigationStatus,
  MonitoringState,
  InvestigationChange,
  AgentDecision,
} from "../../types/api.types";

export type InvestigationListParams = {
  q?: string;
  limit?: number;
  offset?: number;
};

export const listInvestigations = (params?: string | InvestigationListParams, signal?: AbortSignal) => {
  const filters = typeof params === "string" ? { q: params } : params;
  return get<ApiList<Investigation>>(
    `/investigations${queryString({ limit: 100, ...filters })}`,
    signal,
  );
};

export const createInvestigation = (input: InvestigationCreate) =>
  post<InvestigationCreateResponse>("/investigations", input);

export const getInvestigation = (id: string, signal?: AbortSignal) =>
  get<InvestigationDetail>(`/investigations/${encodeURIComponent(id)}`, signal);

export const getInvestigationPlan = (id: string, signal?: AbortSignal) =>
  get<InvestigationPlan>(`/investigations/${encodeURIComponent(id)}/plan`, signal);

export const startResearch = (id: string) =>
  post<ResearchState>(`/investigations/${encodeURIComponent(id)}/research`, {});

export const getResearchState = (id: string, signal?: AbortSignal) =>
  get<ResearchState>(`/investigations/${encodeURIComponent(id)}/research`, signal);

export const getInvestigationEvidence = (id: string, signal?: AbortSignal) =>
  get<ApiList<unknown>>(`/investigations/${encodeURIComponent(id)}/evidence`, signal);

export const getInvestigationEntities = (id: string, signal?: AbortSignal) =>
  get<ApiList<unknown>>(`/investigations/${encodeURIComponent(id)}/entities`, signal);

export const getInvestigationRelationships = (id: string, signal?: AbortSignal) =>
  get<ApiList<unknown>>(`/investigations/${encodeURIComponent(id)}/relationships`, signal);

export const startVerification = (id: string) =>
  post<{ investigation_id: string; status: InvestigationStatus; progress: number; verification_mode: "deterministic" | "local_demo" | null; verification_progress: VerificationProgress | null; error_message: string | null }>(`/investigations/${encodeURIComponent(id)}/verify`, {});

export const getVerificationState = (id: string, signal?: AbortSignal) =>
  get<{ investigation_id: string; status: InvestigationStatus; progress: number; verification_mode: "deterministic" | "local_demo" | null; verification_progress: VerificationProgress | null; error_message: string | null }>(`/investigations/${encodeURIComponent(id)}/verification`, signal);

export const enableMonitoring = (id: string, interval_minutes: number) =>
  post<MonitoringState>(`/investigations/${encodeURIComponent(id)}/monitor`, { interval_minutes });

export const disableMonitoring = (id: string) =>
  remove<MonitoringState>(`/investigations/${encodeURIComponent(id)}/monitor`);

export const runMonitoring = (id: string) =>
  post<{ investigation_id: string; run_id: string; status: string; message: string }>(`/investigations/${encodeURIComponent(id)}/monitor/run`, {});

export const getMonitoringState = (id: string, signal?: AbortSignal) =>
  get<MonitoringState>(`/investigations/${encodeURIComponent(id)}/monitoring`, signal);

export const getInvestigationChanges = (id: string, signal?: AbortSignal) =>
  get<ApiList<InvestigationChange>>(`/investigations/${encodeURIComponent(id)}/changes?limit=25`, signal);

export const getAgentDecisions = (id: string, signal?: AbortSignal) =>
  get<ApiList<AgentDecision>>(`/investigations/${encodeURIComponent(id)}/agent-decisions?limit=25`, signal);
