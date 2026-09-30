import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowRight, Clock3, GitBranch, ShieldCheck, Sparkles, Users } from "lucide-react";
import { createWebSocket } from "../../services/websocket/websocket";
import { getInvestigation } from "../../features/investigations/investigation.api";
import { ErrorState, LoadingState } from "../../components/states/AsyncStates";
import type { InvestigationDetail as InvestigationRecord } from "../../types/api.types";
import "./investigation-details.css";

export default function InvestigationDetails() {
  const navigate = useNavigate();
  const { investigationId } = useParams<{ investigationId: string }>();
  const [record, setRecord] = useState<InvestigationRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [socketStatus, setSocketStatus] = useState("Connecting to progress stream...");

  useEffect(() => {
    if (!investigationId) {
      setError("No investigation ID was provided.");
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    getInvestigation(investigationId, controller.signal)
      .then((data) => { setRecord(data); setError(""); })
      .catch((cause) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Unable to load investigation."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });

    const socket = createWebSocket(`/investigations/${encodeURIComponent(investigationId)}`);
    socket.onopen = () => setSocketStatus("Progress stream connected");
    socket.onclose = () => setSocketStatus("Progress stream disconnected");
    socket.onerror = () => setSocketStatus("Progress stream unavailable");
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as { type?: string; message?: string; investigation?: InvestigationRecord };
        if (message.type === "snapshot" && message.investigation) {
          setRecord(message.investigation as InvestigationRecord);
          setSocketStatus(message.message ?? "Current persisted status received.");
        } else if (message.type === "error") {
          setSocketStatus(message.message ?? "Progress stream returned an error.");
        }
      } catch {
        setSocketStatus("Received an unreadable progress update.");
      }
    };

    return () => { controller.abort(); socket.close(); };
  }, [investigationId]);

  if (loading) return <LoadingState label="Loading investigation..." />;
  if (error || !record) return <ErrorState title="Investigation unavailable" description={error || "The investigation was not found."} action={() => navigate("/investigations")} />;

  const status = record.status.replace(/_/g, " ");
  return (
    <div className="investigation-page">
      <section className="investigation-hero"><div><span className="eyebrow">SAVED INVESTIGATION</span><h1>{record.name}</h1><p>{record.goal}</p><div className="investigation-status"><span className={`status-dot ${record.status === "running" ? "connected" : "disconnected"}`} />{status} · {socketStatus}</div></div></section>
      <section className="glass-section progress-section"><div className="section-heading-row"><div><span className="section-label">RECORDED PROGRESS</span><h2>{Math.round(record.progress)}%</h2></div><div className="progress-status"><Clock3 size={17} />{status}</div></div><div className="progress-track"><div className="progress-fill" style={{ width: `${Math.max(0, Math.min(100, record.progress))}%` }} /></div></section>
      <section className="glass-section"><div className="section-heading-row pipeline-heading"><div><span className="section-label">PROCESSING STATUS</span><h2>Discovery worker</h2></div><span className="agent-count">Not configured</span></div><div className="empty-event"><Sparkles size={20} />The backend stores requests and streams their persisted status. No research agent or background worker is configured.</div></section>
      <section className="glass-section"><div className="section-heading"><span className="section-label">PERSISTED FINDINGS</span><h2>Current investigation data</h2></div><div className="summary-grid"><SummaryCard icon={<Users size={22} />} value={record.entities_count} label="Entities" /><SummaryCard icon={<GitBranch size={22} />} value={record.relationships_count} label="Relationships" /><SummaryCard icon={<ShieldCheck size={22} />} value={record.risk_count} label="Risk records" /><SummaryCard icon={<Clock3 size={22} />} value={record.timeline.length} label="Timeline events" /></div></section>
      <section className="glass-section"><div className="section-heading"><span className="section-label">REQUEST SCOPE</span><h2>Configured scope</h2></div><p>{Object.entries(record.scope).filter(([, enabled]) => enabled).map(([key]) => key).join(" · ") || "No scope selected"} · {record.depth} depth</p><p>Created {new Date(record.created_at).toLocaleString()} · Updated {new Date(record.updated_at).toLocaleString()}</p></section>
      <div className="completion-card"><div className="completion-content"><span>AVAILABLE DATA</span><h2>Explore saved dependencies and evidence.</h2><p>Counts show records actually stored for this investigation.</p></div><button className="graph-button" onClick={() => navigate("/graph")}>Explore Dependency Graph<ArrowRight size={18} /></button></div>
    </div>
  );
}

function SummaryCard({ icon, value, label }: { icon: React.ReactNode; value: number; label: string }) {
  return <div className="summary-card"><div className="summary-icon">{icon}</div><div className="summary-value">{value}</div><div className="summary-label">{label}</div></div>;
}
