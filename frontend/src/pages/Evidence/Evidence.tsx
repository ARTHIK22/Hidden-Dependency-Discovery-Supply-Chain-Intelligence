import { useEffect, useState } from "react";
import { ArrowRight, ExternalLink, FileText, Search, ShieldCheck, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { listEvidence } from "../../features/evidence/evidence.api";
import { ErrorState, LoadingState } from "../../components/states/AsyncStates";
import type { Evidence as EvidenceRecord } from "../../types/api.types";
import "./evidence.css";

type EvidenceItem = EvidenceRecord & { relationship: string; from: string; to: string; status: string };

export default function Evidence() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<EvidenceItem[]>([]);
  const [selected, setSelected] = useState<EvidenceItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    listEvidence(query || undefined, controller.signal)
      .then(({ items: rows }) => {
        setItems(rows.map((row) => ({
          ...row,
          relationship: row.relationship_type || "Unlinked evidence",
          from: row.source_entity_name || "Unknown entity",
          to: row.target_entity_name || "Unknown entity",
          status: row.verification_status.toLowerCase().replace(/_/g, " "),
        })));
        setError(false);
      })
      .catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setError(true); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query]);

  const conflictingEvidenceIds = selected?.relationship_verification?.conflicting_evidence_ids ?? [];

  return <div className="evidence-page">
    <div className="page-heading-row"><div><span className="eyebrow">PROVENANCE</span><h1>Evidence</h1><p>Review source records, the relationship claims they support or contradict, and their provenance.</p></div><div className="evidence-summary"><strong>{items.length}</strong><span>evidence records</span></div></div>
    <div className="evidence-toolbar glass-card"><div className="search-field"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search entities, relationships or sources..." /></div><button className="glass-button" onClick={() => navigate("/graph")}>Open graph<ArrowRight size={16} /></button></div>
    {loading ? <LoadingState label="Loading evidence..." /> : error ? <ErrorState title="Evidence is unavailable" description="Check the backend and PostgreSQL connection." action={() => window.location.reload()} /> : <div className="evidence-list">
      {items.map((item) => <button key={item.id} className="evidence-row glass-card" onClick={() => setSelected(item)}><div className="evidence-icon"><FileText size={19} /></div><div className="evidence-main"><div className="evidence-relationship"><strong>{item.from}</strong><ArrowRight size={14} /><strong>{item.to}</strong><span className="relationship-pill">{item.relationship}</span></div><p>{item.excerpt}</p><span className="evidence-source">{item.title ? `${item.title} · ` : ""}{item.source} · {item.source_type}</span></div><div className="evidence-confidence"><span>{item.confidence === null ? "—" : `${Math.round(item.confidence * 100)}%`}</span><small>confidence</small></div><span className={`status-pill ${item.status === "verified" || item.status === "supporting" ? "verified" : item.status === "conflicting" ? "conflict" : "review"}`}>{item.status}</span></button>)}
      {!items.length && <div className="empty-state glass-card"><Search size={24} /><h3>{query ? "No evidence found" : "No evidence records yet"}</h3><p>{query ? "Try another entity, relationship or source." : "Evidence appears when provenance records are stored."}</p></div>}
    </div>}
    {selected && <div className="drawer-backdrop" onClick={() => setSelected(null)}><aside className="evidence-drawer glass-card" onClick={(event) => event.stopPropagation()}><div className="drawer-header"><div><span className="eyebrow">EVIDENCE RECORD</span><h2>{selected.title || selected.relationship}</h2></div><button className="icon-button" onClick={() => setSelected(null)}><X size={18} /></button></div><div className="drawer-entities"><div><span>FROM</span><strong>{selected.from}</strong></div><ArrowRight size={17} /><div><span>TO</span><strong>{selected.to}</strong></div></div><div className="drawer-score"><ShieldCheck size={18} /><div><strong>{selected.confidence === null ? "Confidence not recorded" : `${Math.round(selected.confidence * 100)}% confidence`}</strong><span>Evidence status: {selected.status}</span></div></div><div className="drawer-section"><span className="drawer-label">SOURCE</span><h3>{selected.source}</h3><p>{selected.source_type} · Published {selected.published_date ? new Date(selected.published_date).toLocaleDateString() : "date not recorded"} · Retrieved {new Date(selected.captured_at).toLocaleDateString()}</p><div className="source-preview"><FileText size={18} /><div><strong>Evidence text</strong><span>{selected.excerpt}</span></div></div>{selected.source_url && <a className="glass-button full" href={selected.source_url} target="_blank" rel="noreferrer">Open source<ExternalLink size={15} /></a>}</div><div className="drawer-section"><span className="drawer-label">RELATIONSHIP VERIFICATION</span><p>{selected.relationship_verification?.status || "Not verified"} · {selected.relationship_verification?.confidence == null ? "confidence not scored" : `${Math.round(selected.relationship_verification.confidence * 100)}% confidence`}</p>{selected.relationship_verification?.explanation && <p>{selected.relationship_verification.explanation}</p>}{conflictingEvidenceIds.length > 0 && <p className="evidence-conflict-note">Contradictory evidence preserved ({conflictingEvidenceIds.length} item(s)). Evidence IDs: {conflictingEvidenceIds.join(", ")}</p>}<button className="relationship-link" onClick={() => navigate("/graph")}>Explore relationship in graph<ArrowRight size={15} /></button></div></aside></div>}
  </div>;
}
