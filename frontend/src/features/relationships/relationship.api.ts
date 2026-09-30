import { get } from "../../services/api/client";
import type { GraphEdge, GraphNode } from "../../types/api.types";

export type RelationshipRecord = {
  id: string;
  source_entity_id: string;
  source_entity_name: string;
  target_entity_id: string;
  target_entity_name: string;
  relationship_type: string;
  confidence: number | null;
  verification_status: string;
};

// The current backend exposes relationship data through the graph endpoint.
export const getDependencyGraph = (signal?: AbortSignal) =>
  get<{ nodes: GraphNode[]; edges: GraphEdge[] }>("/graph", signal);

export const listRelationships = async (signal?: AbortSignal): Promise<RelationshipRecord[]> => {
  const { nodes, edges } = await getDependencyGraph(signal);
  const entityNames = new Map(nodes.map((node) => [node.id, node.data.label]));
  return edges.map((edge) => ({
    id: edge.id,
    source_entity_id: edge.source,
    source_entity_name: entityNames.get(edge.source) ?? edge.source,
    target_entity_id: edge.target,
    target_entity_name: entityNames.get(edge.target) ?? edge.target,
    relationship_type: edge.data.relationshipType,
    confidence: edge.data.confidence,
    verification_status: edge.data.verificationStatus,
  }));
};
