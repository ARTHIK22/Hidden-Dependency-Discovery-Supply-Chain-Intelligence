import { get } from "../../services/api/client";
import type { GraphEdge, GraphNode } from "../../types/api.types";

// The current backend exposes relationship data through the graph endpoint.
export const getDependencyGraph = (signal?: AbortSignal) =>
  get<{ nodes: GraphNode[]; edges: GraphEdge[] }>("/graph", signal);
