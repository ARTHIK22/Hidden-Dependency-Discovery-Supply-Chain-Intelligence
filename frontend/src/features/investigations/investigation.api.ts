import { get, post, queryString } from "../../services/api/client";
import type {
  ApiList,
  Investigation,
  InvestigationCreate,
  InvestigationDetail,
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
  post<{ investigation: Investigation }>("/investigations", input);

export const getInvestigation = (id: string, signal?: AbortSignal) =>
  get<InvestigationDetail>(`/investigations/${encodeURIComponent(id)}`, signal);
