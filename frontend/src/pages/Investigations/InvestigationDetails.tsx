import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Activity, AlertTriangle, ArrowRight, Clock3, GitBranch, Search, ShieldCheck, Sparkles, Users } from "lucide-react";
import { createWebSocket } from "../../services/websocket/websocket";
import {
  disableMonitoring,
  enableMonitoring,
  getAgentDecisions,
  getInvestigation,
  getInvestigationChanges,
  getInvestigationEntities,
  getMonitoringState,
  getVerificationState,
  runMonitoring,
  startResearch,
  startVerification,
} from "../../features/investigations/investigation.api";
import { ErrorState, LoadingState } from "../../components/states/AsyncStates";
import { useToast } from "../../components/toast/ToastProvider";
import type {
  AgentDecision,
  InvestigationChange,
  InvestigationDetail as InvestigationRecord,
  MonitoringState,
  ResearchProgress,
  VerificationProgress,
} from "../../types/api.types";
import "./investigation-details.css";

export default function InvestigationDetails() {
  const navigate = useNavigate();
  const { investigationId } = useParams<{ investigationId: string }>();
  const { toast } = useToast();
  const [record, setRecord] = useState<InvestigationRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState("");
  const [socketStatus, setSocketStatus] = useState("Connecting to progress stream...");

  useEffect(() => {
    if (!investigationId) {
      setError("No investigation ID was provided.");
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    let snapshotMessage = "";
    getInvestigation(investigationId, controller.signal)
      .then((data) => { setRecord(data); setError(""); })
      .catch((cause) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Unable to load investigation."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });

    const socket = createWebSocket(`/investigations/${encodeURIComponent(investigationId)}`);
    socket.onopen = () => setSocketStatus("Progress stream connected");
    socket.onclose = () => setSocketStatus(snapshotMessage || "Progress stream disconnected");
    socket.onerror = () => setSocketStatus("Progress stream unavailable");
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as {
          type?: string;
          message?: string;
          investigation?: InvestigationRecord;
          progress?: ResearchProgress;
          verification?: VerificationProgress;
          event?: { message?: string; type?: string };
        };
        if ((message.type === "snapshot" || message.type === "research_progress") && message.investigation) {
          snapshotMessage = message.message ?? "Current persisted status received.";
          setRecord((current) => current
            ? { ...current, ...message.investigation } as InvestigationRecord
            : message.investigation as InvestigationRecord);
          setSocketStatus(snapshotMessage);
        } else if (message.type === "error") {
          setSocketStatus(message.message ?? "Progress stream returned an error.");
        } else if (message.type?.startsWith("monitoring_") || ["change_detected", "agent_decision", "followup_started", "followup_completed"].includes(message.type ?? "")) {
          const eventMessage = message.event?.message ?? (message.type ?? "monitoring event").replace(/_/g, " ");
          setSocketStatus(eventMessage);
        }
      } catch {
        setSocketStatus("Received an unreadable progress update.");
      }
    };

    return () => { controller.abort(); socket.close(); };
  }, [investigationId]);

  useEffect(() => {
    if (!investigationId || record?.status !== "VERIFYING") return;
    const controller = new AbortController();
    let polling = false;
    const refreshVerification = () => {
      if (polling) return;
      polling = true;
      getVerificationState(investigationId, controller.signal)
        .then((state) => setRecord((current) => current ? {
          ...current, status: state.status, progress: state.progress,
          verification_mode: state.verification_mode,
          verification_progress: state.verification_progress,
          error_message: state.error_message,
        } : current))
        .catch(() => undefined)
        .finally(() => { polling = false; });
    };
    refreshVerification();
    const timer = window.setInterval(refreshVerification, 900);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [investigationId, record?.status]);

  const handleStartResearch = async () => {
    if (!investigationId || starting) return;
    setStarting(true);
    try {
      const state = await startResearch(investigationId);
      setRecord((current) => current
        ? { ...current, status: state.status, progress: state.progress, research_mode: state.research_mode, research_progress: state.research_progress }
        : current);
      toast.success("Research started.");
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : "Unable to start research.");
    } finally {
      setStarting(false);
    }
  };

  const handleStartVerification = async () => {
    if (!investigationId || verifying) return;
    setVerifying(true);
    try {
      const state = await startVerification(investigationId);
      setRecord((current) => current ? {
        ...current, status: state.status, progress: state.progress,
        verification_mode: state.verification_mode,
        verification_progress: state.verification_progress,
        error_message: state.error_message,
      } : current);
      toast.success("Verification started.");
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : "Unable to start verification.");
    } finally {
      setVerifying(false);
    }
  };

  if (loading) return <LoadingState label="Loading investigation..." />;
  if (error || !record) return <ErrorState title="Investigation unavailable" description={error || "The investigation was not found."} action={() => navigate("/investigations")} />;

  const status = record.status.replace(/_/g, " ");
  const research = record.research_progress;
  const verification = record.verification_progress;
  const isResearching = record.status === "RESEARCHING";
  const researchComplete = ["COMPLETED", "RESEARCH_COMPLETED", "VERIFYING", "VERIFICATION_COMPLETED"].includes(record.status);
  const isVerifying = record.status === "VERIFYING";
  const verificationComplete = record.status === "VERIFICATION_COMPLETED";
  const monitoringEligible = ["VERIFICATION_COMPLETED", "RISK_ANALYZED", "COMPLETED"].includes(record.status)
    && Boolean(verification?.finished_at) && !record.demo_mode;
  const isLocalDemo = record.research_mode === "local_demo";

  return (
    <div className="investigation-page">
      <section className="investigation-hero">
        <div>
          <span className="eyebrow">{record.demo_mode ? "DEMO SCENARIO" : "SAVED INVESTIGATION"}</span>
          <h1>{record.name}</h1>
          <p>{record.goal}</p>
          <div className="investigation-status">
            <span className={`status-dot ${["running", "PLANNING", "PLANNED", "RESEARCHING"].includes(record.status) ? "connected" : "disconnected"}`} />
            {status} · {socketStatus}
          </div>
        </div>
      </section>

      <section className="glass-section progress-section">
        <div className="section-heading-row">
          <div><span className="section-label">{isVerifying || verificationComplete ? "VERIFICATION PROGRESS" : "RESEARCH PROGRESS"}</span><h2>{Math.round(record.progress)}%</h2></div>
          <div className="progress-status"><Clock3 size={17} />{isVerifying ? "Verifying" : verificationComplete ? "Verification completed" : isResearching ? "Researching" : researchComplete ? "Research completed" : status}</div>
        </div>
        <div className="progress-track"><div className="progress-fill" style={{ width: `${Math.max(0, Math.min(100, record.progress))}%` }} /></div>
      </section>

      {(researchComplete || isVerifying || verificationComplete || Boolean(verification)) && <section className="glass-section verification-section">
        <div className="section-heading-row pipeline-heading">
          <div><span className="section-label">PHASE 3</span><h2>Verification</h2></div>
          <span className="agent-count">{record.verification_mode === "local_demo" ? "Local demo" : "Deterministic"}</span>
        </div>
        {verificationComplete && <p className="verification-complete-message">Research findings have been resolved and verified against available evidence. Risk analysis has not started.</p>}
        {!verification && !verificationComplete && researchComplete && <div className="research-action-row"><p>Research is complete. Resolve duplicate entities and verify relationships against the collected evidence.</p><button className="research-action" onClick={handleStartVerification} disabled={verifying}>{verifying ? "Starting verification…" : "Start Verification"}<ArrowRight size={16} /></button></div>}
        {verification && <>
          <p className="research-message">{verification.message ?? (isVerifying ? "Verification is running." : "Persisted verification results.")}</p>
          {isVerifying && <div className="progress-track verification-track"><div className="progress-fill" style={{ width: `${verification.total_relationships ? Math.min(100, Math.round(verification.completed_relationships / verification.total_relationships * 100)) : verification.phase === "relationship_verification" ? 100 : 0}%` }} /></div>}
          <div className="summary-grid research-counts">
            <SummaryCard icon={<Users size={22} />} value={verification.total_entities} label={`Entities · ${verification.canonical_entities} canonical`} />
            <SummaryCard icon={<GitBranch size={22} />} value={verification.total_relationships} label="Relationships processed" />
            <SummaryCard icon={<ShieldCheck size={22} />} value={verification.verified_relationships} label="Verified" />
            <SummaryCard icon={<AlertTriangle size={22} />} value={verification.conflicted_relationships} label="Conflicted" />
          </div>
          <div className="verification-breakdown">
            <span>{verification.resolved_aliases} aliases resolved</span><span>{verification.possible_duplicates} possible duplicates</span><span>{verification.unresolved_entities} unresolved identities</span>
            <span>{verification.supported_relationships} supported</span><span>{verification.insufficient_evidence_relationships} insufficient evidence</span><span>{verification.rejected_relationships} rejected</span>
          </div>
          {verificationComplete && <p className="plan-notice">Verification completed; risk analysis is pending. Source conflicts and uncertainty remain visible in the graph.</p>}
        </>}
      </section>}

      {record.plan && <section className="glass-section plan-section">
        <div className="section-heading"><span className="section-label">INVESTIGATION PLAN</span><h2>Structured plan</h2></div>
        <div className="plan-meta">
          <div><span>Status</span><strong>{status}</strong></div>
          <div><span>Planner Mode</span><strong>{record.planner_mode === "llm" ? "LLM" : "Local Demo"}</strong></div>
          <div><span>Target</span><strong>{record.plan.target ?? "Needs clarification"}</strong></div>
          <div><span>Objective</span><strong>{record.plan.objective}</strong></div>
          <div><span>Depth</span><strong>{record.depth} · level {record.plan.depth}</strong></div>
        </div>
        {record.plan.target_clarification && <div className="empty-event plan-clarification"><ShieldCheck size={18} />{record.plan.target_clarification}</div>}
        <PlanList title="Investigation Steps" items={record.plan.steps} ordered />
        <PlanList title="Research Questions" items={record.plan.research_questions} />
        <PlanList title="Expected Entity Types" items={record.plan.entity_types} />
        <PlanList title="Expected Relationship Types" items={record.plan.relationship_types} />
        <PlanList title="Verification Requirements" items={record.plan.verification_requirements} />
        {record.status === "PLANNED" && <div className="research-action-row"><p>The plan is saved. Start research to discover source-backed evidence.</p><button className="research-action" onClick={handleStartResearch} disabled={starting}>{starting ? "Starting research…" : "Start Research"}<ArrowRight size={16} /></button></div>}
        {isResearching && <p className="plan-notice">Research is running from the persisted plan.</p>}
      </section>}

      <section className="glass-section">
        <div className="section-heading-row pipeline-heading">
          <div><span className="section-label">RESEARCH ENGINE</span><h2>{isResearching ? "Research in progress" : researchComplete ? "Research completed" : "Ready for research"}</h2></div>
          <span className="agent-count">{record.research_mode === "external" ? "External provider" : isLocalDemo ? "Demo research mode" : record.plan ? "Not started" : "No plan"}</span>
        </div>
        {isLocalDemo && <div className="research-demo-notice" role="status">Demo research mode — external source discovery is not configured. This run does not generate fictional source records or findings.</div>}
        {record.research_mode === "external" && <div className="research-demo-notice" role="status">Discovered findings are unverified. Entity resolution and verification are pending.</div>}
        {research?.message && <p className="research-message">{research.message}</p>}
        {research && <>
          <div className="research-current-query">
            <span>{research.current_step ? `Step ${research.completed_steps + (isResearching ? 1 : 0)} of ${research.total_steps}` : "Research steps"}</span>
            <strong>{research.current_query ? `Searching: ${research.current_query}` : researchComplete ? "No active query" : "Waiting for research to start"}</strong>
          </div>
          <div className="summary-grid research-counts">
            <SummaryCard icon={<Search size={22} />} value={research.sources_found} label="Sources discovered" />
            <SummaryCard icon={<ShieldCheck size={22} />} value={research.evidence_found} label="Evidence collected" />
            <SummaryCard icon={<Users size={22} />} value={research.entities_found} label="Entities discovered" />
            <SummaryCard icon={<GitBranch size={22} />} value={research.relationships_found} label="Relationships discovered" />
          </div>
          {research.events.length > 0 && <div className="research-timeline"><h3>Research timeline</h3>{research.events.slice().reverse().map((event, index) => <div className="research-event" key={`${event.at}-${event.type}-${index}`}><time>{new Date(event.at).toLocaleTimeString()}</time><span>{event.message}</span></div>)}</div>}
        </>}
        {!research && <div className="empty-event"><Sparkles size={20} />{record.plan ? "Research has not started. Start Research when you are ready." : record.demo_mode ? "Fictional sample entities, relationships, evidence and risks were saved for this demo. They are illustrative and not verified." : "This investigation has no persisted research plan."}</div>}
        {record.error_message && <div className="research-error" role="alert">{record.error_message}</div>}
      </section>

      {monitoringEligible && <MonitoringPanel investigationId={record.id} onOpenFollowup={(id) => navigate(`/investigations/${id}`)} />}

      <section className="glass-section">
        <div className="section-heading"><span className="section-label">PERSISTED FINDINGS</span><h2>Current investigation data</h2></div>
        {researchComplete && record.research_mode === "external" && <p className="research-pending">Discovered — verification pending.</p>}
        <div className="summary-grid">
          <SummaryCard icon={<Users size={22} />} value={record.entities_count} label="Entities" />
          <SummaryCard icon={<GitBranch size={22} />} value={record.relationships_count} label="Relationships" />
          <SummaryCard icon={<ShieldCheck size={22} />} value={record.evidence_count} label="Evidence records" />
          <SummaryCard icon={<Clock3 size={22} />} value={record.risk_count} label="Risk records" />
        </div>
      </section>

      <section className="glass-section"><div className="section-heading"><span className="section-label">REQUEST SCOPE</span><h2>Configured scope</h2></div><p>{Object.entries(record.scope).filter(([, enabled]) => enabled).map(([key]) => key).join(" · ") || "No scope selected"} · {record.depth} depth</p><p>Created {new Date(record.created_at).toLocaleString()} · Updated {new Date(record.updated_at).toLocaleString()}</p></section>
      {record.entities_count > 0 && <div className="completion-card"><div className="completion-content"><span>AVAILABLE DATA</span><h2>Explore saved dependencies and evidence.</h2><p>Relationships discovered during research are not verified yet.</p></div><button className="graph-button" onClick={() => navigate("/graph")}>Explore Dependency Graph<ArrowRight size={18} /></button></div>}
    </div>
  );
}

function MonitoringPanel({ investigationId, onOpenFollowup }: { investigationId: string; onOpenFollowup: (id: string) => void }) {
  const { toast } = useToast();
  const [state, setState] = useState<MonitoringState | null>(null);
  const [changes, setChanges] = useState<InvestigationChange[]>([]);
  const [decisions, setDecisions] = useState<AgentDecision[]>([]);
  const [entityNames, setEntityNames] = useState<Record<string, string>>({});
  const [timeline, setTimeline] = useState<Array<Record<string, unknown>>>([]);
  const [intervalMinutes, setIntervalMinutes] = useState(60);
  const [busy, setBusy] = useState(false);
  const [panelError, setPanelError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    let loading = false;
    const refresh = async () => {
      if (loading) return;
      loading = true;
      try {
        const [monitoring, changeRows, decisionRows, investigation, entityRows] = await Promise.all([
          getMonitoringState(investigationId, controller.signal),
          getInvestigationChanges(investigationId, controller.signal),
          getAgentDecisions(investigationId, controller.signal),
          getInvestigation(investigationId, controller.signal),
          getInvestigationEntities(investigationId, controller.signal),
        ]);
        if (!controller.signal.aborted) {
          const names: Record<string, string> = {};
          for (const item of entityRows.items) {
            const entity = item as { id?: unknown; name?: unknown };
            if (typeof entity.id === "string" && typeof entity.name === "string") names[entity.id] = entity.name;
          }
          setState(monitoring);
          setChanges(changeRows.items);
          setDecisions(decisionRows.items);
          setEntityNames(names);
          setTimeline(investigation.timeline.filter((event) => typeof event.type === "string" && (
            String(event.type).startsWith("monitoring_") || ["change_detected", "agent_decision", "followup_started", "followup_completed", "alert_created"].includes(String(event.type))
          )).slice(-12).reverse());
          setPanelError("");
        }
      } catch (cause) {
        if (!controller.signal.aborted) setPanelError(cause instanceof Error ? cause.message : "Monitoring details are unavailable.");
      } finally {
        loading = false;
      }
    };
    void refresh();
    const timer = window.setInterval(refresh, state?.enabled ? 5000 : 15000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [investigationId, state?.enabled]);

  const act = async (operation: () => Promise<MonitoringState | { run_id: string }>, success: string) => {
    if (busy) return;
    setBusy(true);
    try {
      const result = await operation();
      if ("enabled" in result) setState(result);
      else setState((current) => current ? {
        ...current,
        status: "MONITORING_RUNNING",
        last_run: {
          id: result.run_id,
          status: "MONITORING_RUNNING",
          started_at: new Date().toISOString(),
          finished_at: null,
          change_count: 0,
          decision_count: 0,
          result_json: {},
          error_message: null,
        },
      } : current);
      toast.success(success);
      setPanelError("");
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Monitoring request failed.";
      setPanelError(message);
      toast.error(message);
    } finally {
      setBusy(false);
    }
  };

  const enabled = Boolean(state?.enabled);
  const runActive = state?.status === "MONITORING_RUNNING";
  const statusText = (state?.status ?? "MONITORING_DISABLED").replace(/_/g, " ");

  return (
    <section className="glass-section monitoring-panel" aria-label="Continuous monitoring">
      <div className="section-heading-row pipeline-heading">
        <div><span className="section-label">PHASE 7 · CONTINUOUS OBSERVATION</span><h2><Activity size={20} /> Investigation monitoring</h2></div>
        <span className={`monitoring-state-pill ${enabled ? "is-enabled" : ""}`}>{statusText}</span>
      </div>
      <p className="monitoring-intro">Compare saved graph, evidence, verification, risk, alerts, and your watchlist over time. Safe follow-ups use the existing investigation pipeline.</p>
      <div className="monitoring-stats">
        <div><span>Last checked</span><strong>{state?.last_checked_at ? new Date(state.last_checked_at).toLocaleString() : "Not checked yet"}</strong></div>
        <div><span>Next check</span><strong>{enabled && state?.next_check_at ? new Date(state.next_check_at).toLocaleString() : "Manual only"}</strong></div>
        <div><span>Graph version</span><strong title={state?.graph_version ?? undefined}>{state?.graph_version ? state.graph_version.slice(0, 12) : "No snapshot"}</strong></div>
        <div><span>Observed records</span><strong>{state ? `${state.entity_count} entities · ${state.relationship_count} relationships · ${state.evidence_count} evidence` : "Loading…"}</strong></div>
      </div>
      <div className="monitoring-controls">
        {!enabled && <label>Check interval
          <select aria-label="Monitoring interval" value={intervalMinutes} onChange={(event) => setIntervalMinutes(Number(event.target.value))} disabled={busy}>
            <option value={15}>Every 15 minutes</option><option value={60}>Every hour</option><option value={240}>Every 4 hours</option><option value={1440}>Daily</option>
          </select>
        </label>}
        {!enabled
          ? <button className="research-action" onClick={() => void act(() => enableMonitoring(investigationId, intervalMinutes), "Monitoring enabled.")} disabled={busy}>{busy ? "Enabling…" : "Enable Monitoring"}<Activity size={16} /></button>
          : <>
            <button className="research-action" onClick={() => void act(() => runMonitoring(investigationId), "Monitoring run started.")} disabled={busy || runActive}>{runActive ? "Monitoring…" : "Run Now"}<ArrowRight size={16} /></button>
            <button className="monitoring-disable" onClick={() => void act(() => disableMonitoring(investigationId), "Monitoring disabled.")} disabled={busy}><span>Disable Monitoring</span></button>
          </>}
      </div>
      {state?.last_error && <div className="research-error" role="alert">{state.last_error}</div>}
      {panelError && <div className="research-error" role="alert">{panelError}</div>}
      <div className="monitoring-columns">
        <div className="monitoring-list-block">
          <h3>Detected changes <span>{changes.length}</span></h3>
          {changes.length === 0 ? <p className="monitoring-empty">No changes detected yet.</p> : changes.slice(0, 8).map((change) => (
            <article className="monitoring-item" key={change.id}>
              <strong>{change.change_type.replace(/_/g, " ")}</strong>
              <time>{new Date(change.created_at).toLocaleString()}</time>
              <p>{summarizeMonitoringChange(change, entityNames)}</p>
              <small>{change.evidence_ids.length ? `${change.evidence_ids.length} evidence reference${change.evidence_ids.length === 1 ? "" : "s"}` : change.relationship_id ? `Relationship ${change.relationship_id.slice(0, 8)}` : change.entity_id ? entityNames[change.entity_id] ?? `Entity ${change.entity_id.slice(0, 8)}` : "Investigation state"}</small>
            </article>
          ))}
        </div>
        <div className="monitoring-list-block">
          <h3>Agent decisions <span>{decisions.length}</span></h3>
          {decisions.length === 0 ? <p className="monitoring-empty">The agent has not made a monitoring decision yet.</p> : decisions.slice(0, 8).map((decision) => (
            <article className="monitoring-item decision-item" key={decision.id}>
              <div><strong>{decision.decision.replace(/_/g, " ")}</strong><span className={`decision-priority priority-${decision.priority}`}>{decision.priority}</span></div>
              <p>{decision.reason}</p>
              <small>{decision.trigger_event.replace(/_/g, " ")} · {decision.status.replace(/_/g, " ")}</small>
              {decision.followup_investigation_id && <button type="button" onClick={() => onOpenFollowup(decision.followup_investigation_id!)}>Open follow-up investigation <ArrowRight size={14} /></button>}
            </article>
          ))}
        </div>
      </div>
      <div className="monitoring-timeline">
        <h3>Agent activity timeline</h3>
        {timeline.length === 0 ? <p className="monitoring-empty">Monitoring activity will appear here after it is enabled.</p> : timeline.map((event, index) => (
          <div className="monitoring-timeline-event" key={String(event.id ?? `${event.type}-${index}`)}>
            <time>{typeof event.at === "string" ? new Date(event.at).toLocaleTimeString() : ""}</time>
            <span><strong>{String(event.type).replace(/_/g, " ")}</strong>{typeof event.message === "string" ? ` · ${event.message}` : ""}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function summarizeMonitoringChange(change: InvestigationChange, entityNames: Record<string, string>): string {
  const before = change.before_value ?? {};
  const after = change.after_value ?? {};
  const relation = Object.keys(after).length ? after : before;
  const label = (id: unknown) => typeof id === "string" ? entityNames[id] ?? id.slice(0, 8) : "unknown entity";
  const beforeScore = before.score;
  const afterScore = after.score;
  if (typeof beforeScore === "number" && typeof afterScore === "number") {
    return `Risk score changed from ${beforeScore}/100 to ${afterScore}/100.`;
  }
  const beforeStatus = before.verification_status;
  const afterStatus = after.verification_status;
  if (typeof beforeStatus === "string" || typeof afterStatus === "string") {
    return `Verification changed from ${typeof beforeStatus === "string" ? beforeStatus : "unknown"} to ${typeof afterStatus === "string" ? afterStatus : "unknown"}.`;
  }
  if (typeof relation.provider_id === "string" && typeof relation.consumer_id === "string") {
    return `Provider ${label(relation.provider_id)} → consumer ${label(relation.consumer_id)}.`;
  }
  if (typeof change.entity_id === "string" && change.change_type === "NEW_ENTITY") {
    return `Added entity ${entityNames[change.entity_id] ?? change.entity_id.slice(0, 8)}.`;
  }
  if (typeof relation.source_id === "string" && typeof relation.target_id === "string") {
    const type = typeof relation.relationship_type === "string" ? relation.relationship_type.replace(/_/g, " ").toLowerCase() : "relationship";
    return `${label(relation.source_id)} ${type} ${label(relation.target_id)}.`;
  }
  if (change.evidence_ids.length) {
    return `${change.evidence_ids.length} persisted evidence reference${change.evidence_ids.length === 1 ? "" : "s"} changed.`;
  }
  return "Persisted investigation state changed.";
}

function PlanList({ title, items, ordered = false }: { title: string; items: string[]; ordered?: boolean }) {
  const List = ordered ? "ol" : "ul";
  return <div className="plan-list-section"><h3>{title}</h3><List className="plan-list">{items.map((item) => <li key={item}>{item}</li>)}</List></div>;
}

function SummaryCard({ icon, value, label }: { icon: React.ReactNode; value: number; label: string }) {
  return <div className="summary-card"><div className="summary-icon">{icon}</div><div className="summary-value">{value}</div><div className="summary-label">{label}</div></div>;
}
