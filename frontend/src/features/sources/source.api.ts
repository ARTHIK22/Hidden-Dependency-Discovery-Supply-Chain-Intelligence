import { apiClient } from "../../services/api/client";
import type { Source, SourceCreate } from "../../types/source.types";
export const listSources = (params: { limit?: number; offset?: number } = {}) => apiClient.get<Source[]>("/sources", params);
export const createSource = (payload: SourceCreate) => apiClient.post<Source>("/sources", payload);
