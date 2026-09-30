import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft, CheckCircle2, Circle, Play, RefreshCw, Sparkles } from "lucide-react";
import { getInvestigation, getInvestigationSteps, startInvestigation } from "../../features/investigations/investigation.api";
import type { Investigation, InvestigationStep } from "../../types/investigation.types";
import { userMessage } from "../../services/api/errors";
import "./investigation-details.css";

export default function InvestigationDetails() {
  const navigate = useNavigate();
  const { investigationId: routeId } = useParams();
  const investigationId = routeId || sessionStorage.getItem("active_investigation_id");
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [steps, setSteps] = useState<InvestigationStep[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!investigationId) { setError("Choose an investigation from the dashboard."); setLoading(false); return; }
    setLoading(true); setError("");
    try {
      const [item, timeline] = await Promise.all([getInvestigation(investigationId), getInvestigationSteps(investigationId)]);
      setInvestigation(item); setSteps(timeline);
    } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); }
  }, [investigationId]);
  useEffect(() => { void load(); }, [load]);
  async function start() {
    if (!investigationId) return;
    setBusy(true); setError("");
    try { const item = await startInvestigation(investigationId); setInvestigation(item); await load(); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  const output = useMemo(() => Object.fromEntries(steps.map((step) => [step.stage, step.output_data])), [steps]);
  const graph = output.graph as { node_count?: number; edge_count?: number } | undefined;
  const extraction = output.extraction as { evidence_processed?: number; relationship_candidates?: unknown[] } | undefined;
  const risk = output.risk as { risks?: unknown[] } | undefined;
  const research = output.research as { reason?: string } | undefined;
  const completed = steps.filter((step) => ["completed", "skipped"].includes(step.status)).length;
  if (loading) return <main className="investigation-page"><p>Loading investigation…</p></main>;
  if (error && !investigation) return <main className="investigation-page"><div role="alert">{error}</div><button onClick={() => void load()}>Retry</button><button onClick={() => navigate("/")}>Back to dashboard</button></main>;
  return <main className="investigation-page">
    <section className="investigation-hero"><div><button type="button" onClick={() => navigate("/")}><ArrowLeft size={16} /> Dashboard</button><span className="eyebrow">INVESTIGATION</span><h1>{investigation?.name}</h1><p>{investigation?.target || investigation?.description || "No target or description provided."}</p><div className="investigation-status"><span className={`status-dot ${investigation?.status}`} />{investigation?.status}</div></div></section>
    {error && <p role="alert" className="auth-error">{error}</p>}
    <section className="glass-section progress-section"><div className="section-heading-row"><div><span className="section-label">RECORDED WORKFLOW</span><h2>{steps.length ? Math.round(completed / 9 * 100) : 0}%</h2></div><div className="progress-status">{investigation?.status}</div></div><div className="progress-track"><div className="progress-fill" style={{ width: `${steps.length ? completed / 9 * 100 : 0}%` }} /></div>
      {investigation && ["draft", "paused", "failed"].includes(investigation.status) && <button type="button" disabled={busy} onClick={start}><Play size={16} />{busy ? "Processing…" : investigation.status === "draft" ? "Start analysis" : "Resume analysis"}</button>}
      <button type="button" onClick={() => void load()}><RefreshCw size={15} />Refresh timeline</button>
    </section>
    <section className="glass-section"><div className="section-heading-row"><div><span className="section-label">TIMELINE</span><h2>Investigation stages</h2></div></div>{steps.length === 0 ? <p>No workflow steps are recorded yet.</p> : <ol className="event-feed">{steps.map((step) => <li className="event-row" key={step.id}><div className="event-icon">{step.status === "completed" ? <CheckCircle2 size={17} /> : step.status === "failed" ? <AlertTriangle size={17} /> : step.status === "skipped" ? <Circle size={17} /> : <Sparkles size={17} />}</div><div className="event-content"><div><strong>{step.stage.split("_").join(" ")}</strong><span className="event-status">{step.status}</span></div><p>{step.status === "skipped" ? research?.reason || "This stage is not configured." : step.error_message || stageSummary(step)}</p><small>{step.completed_at ? new Date(step.completed_at).toLocaleString() : ""}</small></div></li>)}</ol>}</section>
    <section className="summary-grid"><SummaryCard value={graph?.node_count ?? 0} label="Graph entities" /><SummaryCard value={graph?.edge_count ?? 0} label="Recorded relationships" /><SummaryCard value={extraction?.evidence_processed ?? 0} label="Evidence records reviewed" /><SummaryCard value={risk?.risks?.length ?? 0} label="Risk signals" /></section>
    {extraction?.relationship_candidates?.length ? <p>Potential relationship candidates: {extraction.relationship_candidates.length}. Candidates are not automatically stored as facts.</p> : null}
    <p><AlertTriangle size={15} /> External research is skipped. Results are derived from records already in the backend.</p>
  </main>;
}

function stageSummary(step: InvestigationStep): string {
  const value = step.output_data;
  if (step.stage === "extraction") return `${value.evidence_processed ?? 0} evidence records scanned; candidate extraction is review-only.`;
  if (step.stage === "graph") return `${value.node_count ?? 0} entities and ${value.edge_count ?? 0} evidence-linked relationships.`;
  if (step.stage === "verification") return `${value.claims_checked ?? 0} stored claims checked.`;
  if (step.stage === "risk") return `${Array.isArray(value.risks) ? value.risks.length : 0} structural risk signals.`;
  return "Stage completed using recorded data.";
}
function SummaryCard({ value, label }: { value: number; label: string }) { return <div className="summary-card"><div className="summary-value">{value}</div><div className="summary-label">{label}</div></div>; }
