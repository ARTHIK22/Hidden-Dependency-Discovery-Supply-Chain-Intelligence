export type ApiList<T> = { items: T[]; total: number };

export type DashboardSummary = {
  total_investigations: number;
  active_investigations: number;
  discovered_entities: number;
  relationships: number;
  high_risk_dependencies: number;
  unread_alerts: number;
  recent_investigations: Investigation[];
};

export type Investigation = {
  id: string;
  name: string;
  goal: string;
  status: string;
  progress: number;
  scope: Record<string, boolean>;
  depth: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type InvestigationDetail = Investigation & {
  entities_count: number;
  relationships_count: number;
  risk_count: number;
  timeline: Array<Record<string, string>>;
};

export type InvestigationCreate = {
  name?: string;
  goal: string;
  depth: "standard" | "deep" | "maximum";
  scope_geography: boolean;
  scope_materials: boolean;
  scope_manufacturers: boolean;
  scope_verification: boolean;
};

export type Entity = {
  id: string;
  name: string;
  entity_type: string;
  description: string | null;
  jurisdiction: string | null;
  risk_score: number | null;
  risk_level: string | null;
  identifiers: unknown[];
  created_at: string;
};

export type EntityConnection = {
  id: string;
  relationship_type: string;
  direction: "incoming" | "outgoing";
  entity_id: string;
  entity_name: string;
  confidence: number | null;
  verification_status: string;
};

export type EntityDetail = Entity & { connections: EntityConnection[] };

export type Evidence = {
  id: string;
  relationship_id: string | null;
  relationship_type: string | null;
  source_entity_id: string | null;
  source_entity_name: string | null;
  target_entity_id: string | null;
  target_entity_name: string | null;
  source: string;
  source_type: string;
  published_date: string | null;
  captured_at: string;
  confidence: number | null;
  verification_status: string;
  excerpt: string;
  source_url: string | null;
};

export type GraphNode = {
  id: string;
  type: "entity";
  position: { x: number; y: number };
  data: { label: string; type: string; risk: number; status: string; entityId: string };
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  label: string;
  data: {
    relationshipId: string;
    relationshipType: string;
    confidence: number | null;
    source: string | null;
    evidence: string | null;
    verificationStatus: string;
  };
};

export type Risk = {
  id: string;
  entity_id: string;
  entity_name: string;
  entity_type: string;
  investigation_id: string | null;
  score: number;
  level: string;
  reason: string;
  created_at: string;
};

export type Alert = {
  id: string;
  investigation_id: string | null;
  entity_id: string | null;
  entity_name: string | null;
  title: string;
  message: string;
  severity: string;
  read_at: string | null;
  dismissed_at: string | null;
  created_at: string;
};

export type WatchlistEntry = {
  id: string;
  entity_id: string;
  status: string;
  created_at: string;
  entity_name: string;
  entity_type: string;
  risk_score: number | null;
  risk_level: string | null;
};

export type Report = {
  id: string;
  investigation_id: string;
  title: string;
  content: string;
  created_at: string;
};
