import { get, queryString } from "../../services/api/client";
import type { ApiList, Risk } from "../../types/api.types";

export const listRisks = (level?: string, signal?: AbortSignal) =>
  get<ApiList<Risk>>(`/risks${queryString({ level, limit: 250 })}`, signal);

export const getRiskSummary = (signal?: AbortSignal) =>
  get<{ total: number; high_risk: number; average_score: number }>("/risks/summary", signal);
