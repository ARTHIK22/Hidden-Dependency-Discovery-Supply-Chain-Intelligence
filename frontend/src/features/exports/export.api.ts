import { apiClient } from "../../services/api/client";
import type { GraphData } from "../../types/graph.types";
export const getGraph = (entityId: string, depth = 1) => apiClient.get<GraphData>(`/graph/${encodeURIComponent(entityId)}`, { depth });
export const getDependencyPath = (sourceId: string, targetId: string) => apiClient.get<{ path: string[]; hops: number }>(`/graph/path/${encodeURIComponent(sourceId)}/${encodeURIComponent(targetId)}`);
export const exportGraph = () => apiClient.get<GraphData>("/exports/graph.json");
export const exportRelationshipsCsv = () => apiClient.get<Blob>("/exports/relationships.csv");
