import { get, post, queryString } from "../../services/api/client";
import type {
  ApiList,
  Investigation,
  InvestigationCreate,
  InvestigationDetail,
} from "../../types/api.types";

export const listInvestigations = (q?: string, signal?: AbortSignal) =>
  get<ApiList<Investigation>>(
    `/investigations${queryString({ q, limit: 100 })}`,
    signal,
  );

export const createInvestigation = (input: InvestigationCreate) =>
  post<{ investigation: Investigation }>("/investigations", input);

export const getInvestigation = (id: string, signal?: AbortSignal) =>
  get<InvestigationDetail>(`/investigations/${encodeURIComponent(id)}`, signal);
