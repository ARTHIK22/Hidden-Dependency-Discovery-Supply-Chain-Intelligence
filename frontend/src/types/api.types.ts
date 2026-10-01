export type ApiList<T> = { items: T[]; total: number };

export type PlannerMode = "local_demo" | "llm";

export type InvestigationStatus =
  | "QUEUED"
  | "PLANNING"
  | "PLANNED"
  | "RESEARCHING"
  | "RESEARCH_COMPLETED"
  | "VERIFYING"
  | "VERIFICATION_COMPLETED"
  | "RISK_ANALYZING"
  | "RISK_ANALYZED"
  | "COMPLETED"
  | "FAILED"
  | "draft"
  | "queued"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "archived";

export type InvestigationPlan = {
  target: string | null;
  normalized_goal: string;
  objective: string;
  depth: number;
  steps: string[];
  research_questions: string[];
  entity_types: string[];
  relationship_types: string[];
  verification_requirements: string[];
  planner_mode: PlannerMode;
  target_clarification: string | null;
};

export type DashboardSummary = {
  total_investigations: number;
  active_investigations: number;
  completed_investigations?: number;
  discovered_entities: number;
  relationships: number;
  high_risk_dependencies: number;
  unread_alerts: number;
  watchlist_items?: number;
  recent_investigations: Investigation[];
  demo_mode?: boolean;
};

export type Investigation = {
  id: string;
  name: string;
  goal: string;
  status: InvestigationStatus;
  progress: number;
  scope: Record<string, boolean>;
  depth: string;
  objective: string | null;
  plan: InvestigationPlan | null;
  planner_mode: PlannerMode | null;
  research_mode: "local_demo" | "external" | null;
  research_progress: ResearchProgress | null;
  verification_mode?: "deterministic" | "local_demo" | null;
  verification_progress?: VerificationProgress | null;
  risk_progress?: Record<string, unknown> | null;
  risk_analysis?: Record<string, unknown> | null;
  autonomous_context?: Record<string, unknown> | null;
  lifecycle_events?: Array<Record<string, unknown>>;
  error_message: string | null;
  demo_mode?: boolean;
  created_at: string;
  updated_at: string;
};

export type InvestigationDetail = Investigation & {
  entities_count: number;
  relationships_count: number;
  evidence_count: number;
  risk_count: number;
  timeline: Array<Record<string, unknown>>;
};

export type MonitoringStatus =
  | "MONITORING_ENABLED"
  | "MONITORING_DISABLED"
  | "MONITORING_RUNNING"
  | "MONITORING_COMPLETED"
  | "MONITORING_FAILED";

export type MonitoringRun = {
  id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  change_count: number;
  decision_count: number;
  result_json: Record<string, unknown>;
  error_message: string | null;
};

export type MonitoringState = {
  investigation_id: string;
  enabled: boolean;
  status: MonitoringStatus;
  interval_minutes: number;
  max_autonomous_depth: number;
  last_checked_at: string | null;
  next_check_at: string | null;
  last_error: string | null;
  graph_version: string | null;
  entity_count: number;
  relationship_count: number;
  evidence_count: number;
  last_run: MonitoringRun | null;
};

export type InvestigationChange = {
  id: string;
  investigation_id: string;
  run_id: string;
  change_type: string;
  entity_id: string | null;
  relationship_id: string | null;
  before_value: Record<string, unknown> | null;
  after_value: Record<string, unknown> | null;
  evidence_ids: string[];
  created_at: string;
};

export type AgentDecision = {
  id: string;
  investigation_id: string;
  run_id: string;
  trigger_event: string;
  decision: string;
  reason: string;
  entity_id: string | null;
  relationship_id: string | null;
  priority: string;
  evidence_ids: string[];
  status: string;
  result: string | null;
  followup_investigation_id: string | null;
  created_at: string;
};

export type ResearchEvent = {
  at: string;
  type: string;
  message: string;
  step_id?: string | null;
  query?: string | null;
};

export type ResearchProgress = {
  mode: "local_demo" | "external";
  current_step: string | null;
  completed_steps: number;
  total_steps: number;
  current_query: string | null;
  sources_found: number;
  evidence_found: number;
  entities_found: number;
  relationships_found: number;
  elapsed_seconds: number;
  started_at: string | null;
  updated_at: string | null;
  finished_at: string | null;
  message: string | null;
  events: ResearchEvent[];
};

export type VerificationProgress = {
  mode: "deterministic" | "local_demo";
  resolution_mode: "deterministic";
  phase: string;
  completed_entities: number;
  total_entities: number;
  canonical_entities: number;
  resolved_aliases: number;
  possible_duplicates: number;
  unresolved_entities: number;
  completed_relationships: number;
  total_relationships: number;
  relationship_candidates: number;
  verified_relationships: number;
  supported_relationships: number;
  conflicted_relationships: number;
  rejected_relationships: number;
  insufficient_evidence_relationships: number;
  started_at: string | null;
  updated_at: string | null;
  finished_at: string | null;
  message: string | null;
  events: Array<{ at: string; type: string; message: string }>;
};

export type ResearchState = {
  investigation_id: string;
  status: InvestigationStatus;
  progress: number;
  research_mode: "local_demo" | "external" | null;
  research_progress: ResearchProgress | null;
  error_message: string | null;
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

export type InvestigationCreateResponse = {
  investigation: Investigation;
  plan: InvestigationPlan;
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
  normalized_name?: string | null;
  aliases?: string[];
  canonical_entity_id?: string | null;
  canonical_entity_name?: string | null;
  resolution_status?: string | null;
  resolution_confidence?: number | null;
  evidence_count?: number;
  sources?: string[];
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
  title?: string | null;
  metadata?: Record<string, unknown>;
  relationship_verification?: {
    status?: string;
    confidence?: number;
    explanation?: string;
    supporting_evidence_ids?: string[];
    conflicting_evidence_ids?: string[];
    evidence_ids?: string[];
  } | null;
};

export type GraphNode = {
  id: string;
  type: "entity";
  position: { x: number; y: number };
  data: { label: string; type: string; risk: number | null; riskLevel?: string | null; riskStatus?: string; riskReason?: string | null; riskFactors?: RiskFactor[]; propagatedRisk?: number | null; status: string; entityId: string; demoOnly?: boolean; researchMode?: string | null; aliases?: string[]; resolutionStatus?: string | null; resolutionConfidence?: number | null; evidenceCount?: number; sources?: string[] };
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
    demoOnly?: boolean;
    researchMode?: string | null;
    evidenceCount?: number;
    evidenceTruncated?: boolean;
    sources?: string[];
    supportingEvidenceCount?: number;
    conflictingEvidenceCount?: number;
    conflictFlag?: boolean;
    verifiedAt?: string | null;
    verification?: Record<string, unknown>;
    riskScore?: number | null;
    riskLevel?: string | null;
    riskReason?: string | null;
    riskFactors?: RiskFactor[];
    evidenceItems?: Array<{
      id: string;
      source: string;
      sourceType: string;
      url: string | null;
      title: string;
      excerpt: string;
      capturedAt: string | null;
      publishedDate: string | null;
      verificationStatus: string;
    }>;
  };
};

export type RiskFactor = {
  key: string;
  label: string;
  status: "KNOWN" | "UNKNOWN" | string;
  score: number | null;
  explanation: string;
  source: string | null;
  evidence_ids: string[];
};

export type Risk = {
  id: string;
  entity_id: string;
  entity_name: string;
  entity_type: string;
  investigation_id: string | null;
  relationship_id?: string | null;
  snapshot_id?: string | null;
  target_type?: string;
  score: number | null;
  local_score?: number | null;
  propagated_score?: number | null;
  level: string;
  reason: string;
  risk_factors?: RiskFactor[];
  demo_mode?: boolean;
  created_at: string;
};

export type Alert = {
  id: string;
  investigation_id: string | null;
  entity_id: string | null;
  relationship_id?: string | null;
  entity_name: string | null;
  title: string;
  message: string;
  alert_type?: string;
  severity: string;
  reason?: string | null;
  risk_score?: number | null;
  evidence_ids?: string[];
  risk_snapshot?: Record<string, unknown> | null;
  demo_only?: boolean;
  read_at: string | null;
  dismissed_at: string | null;
  created_at: string;
};

export type WatchlistEntry = {
  id: string;
  target_type?: "entity" | "relationship" | "investigation" | "risk_condition";
  target_id?: string | null;
  entity_id: string | null;
  relationship_id?: string | null;
  investigation_id?: string | null;
  status: string;
  created_at: string;
  entity_name: string;
  entity_type: string;
  risk_score: number | null;
  risk_level: string | null;
  risk_threshold?: number | null;
  condition_json?: Record<string, unknown>;
  is_demo?: boolean;
};

export type Report = {
  id: string;
  investigation_id: string;
  title: string;
  content: string;
  structured_content?: Record<string, unknown> | null;
  created_at: string;
};
