import { apiClient } from "../../services/api/client";
import type { Entity, EntityAlias, EntityCreate, EntityUpdate } from "../../types/entity.types";
export const listEntities = (params: { q?: string; limit?: number; offset?: number } = {}) => apiClient.get<Entity[]>("/entities", params);
export const createEntity = (payload: EntityCreate) => apiClient.post<Entity>("/entities", payload);
export const getEntity = (id: string) => apiClient.get<Entity>(`/entities/${encodeURIComponent(id)}`);
export const updateEntity = (id: string, payload: EntityUpdate) => apiClient.patch<Entity>(`/entities/${encodeURIComponent(id)}`, payload);
export const listAliases = (id: string) => apiClient.get<EntityAlias[]>(`/entities/${encodeURIComponent(id)}/aliases`);
export const addAlias = (id: string, alias: string, alias_type = "name") => apiClient.post<EntityAlias>(`/entities/${encodeURIComponent(id)}/aliases`, { alias, alias_type });
