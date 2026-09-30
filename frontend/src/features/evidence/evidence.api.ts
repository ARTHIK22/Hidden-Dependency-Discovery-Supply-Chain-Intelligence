import { get, queryString } from "../../services/api/client";
import type { ApiList, Evidence } from "../../types/api.types";

export const listEvidence = (q?: string, signal?: AbortSignal) =>
  get<ApiList<Evidence>>(`/evidence${queryString({ q, limit: 250 })}`, signal);

export const getEvidence = (id: string, signal?: AbortSignal) =>
  get<Evidence>(`/evidence/${encodeURIComponent(id)}`, signal);
