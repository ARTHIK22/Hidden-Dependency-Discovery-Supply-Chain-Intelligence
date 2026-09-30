import { apiClient } from "../../services/api/client";
import type { Relationship, RelationshipCreate, RelationshipVerification } from "../../types/relationship.types";
export const listRelationships = (params: { entity_id?: string; limit?: number; offset?: number } = {}) => apiClient.get<Relationship[]>("/relationships", params);
export const getRelationship = (id: string) => apiClient.get<Relationship>(`/relationships/${encodeURIComponent(id)}`);
export const createRelationship = (payload: RelationshipCreate) => apiClient.post<Relationship>("/relationships", payload);
export const verifyRelationship = (id: string) => apiClient.post<RelationshipVerification>(`/relationships/${encodeURIComponent(id)}/verify`);
