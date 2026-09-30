import { apiClient } from "../../services/api/client";
import type { Evidence, EvidenceCreate } from "../../types/evidence.types";
export const listEvidence = (params: { relationship_id?: string; entity_id?: string; limit?: number; offset?: number } = {}) => apiClient.get<Evidence[]>("/evidence", params);
export const createEvidence = (payload: EvidenceCreate) => apiClient.post<Evidence>("/evidence", payload);
