export interface GraphNode { id: string; name: string; type: string }
export interface GraphEdge { id: string; source: string; target: string; type: string; confidence: number; verification_status: string }
export interface GraphData { nodes: GraphNode[]; edges: GraphEdge[] }
export interface WatchlistItem { id: string; user_id: string; entity_id: string; name: string | null; created_at: string }
