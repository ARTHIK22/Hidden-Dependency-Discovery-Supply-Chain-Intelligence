import { useEffect, useState } from "react";
import { ArrowRight, Building2, Factory, Globe2, Layers3, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { getEntity, listEntities } from "../../features/entities/entity.api";
import { ErrorState, LoadingState } from "../../components/states/AsyncStates";
import type { Entity as EntityRecord, EntityDetail } from "../../types/api.types";
import "./entity-explorer.css";

function EntityIcon({ type }: { type: string }) {
  const normalized = type.toLowerCase();
  if (normalized.includes("company")) return <Building2 size={17} />;
  if (normalized.includes("manufacturer") || normalized.includes("facility")) return <Factory size={17} />;
  if (normalized.includes("region")) return <Globe2 size={17} />;
  return <Layers3 size={17} />;
}

export default function EntityExplorer() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<EntityRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<EntityDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    listEntities(query || undefined, controller.signal)
      .then(({ items: data }) => {
        setItems(data);
        setError(false);
        setSelectedId((current) => current && data.some((item) => item.id === current) ? current : data[0]?.id ?? null);
      })
      .catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setError(true); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query]);

  useEffect(() => {
    if (!selectedId) { setSelected(null); return; }
    const controller = new AbortController();
    setDetailLoading(true);
    getEntity(selectedId, controller.signal)
      .then(setSelected)
      .catch((cause) => { if (!controller.signal.aborted) console.error(cause); })
      .finally(() => { if (!controller.signal.aborted) setDetailLoading(false); });
    return () => controller.abort();
  }, [selectedId]);

  return <div className="entity-page">
    <div className="entity-heading"><div><span className="eyebrow">ENTITY INTELLIGENCE</span><h1>Entity Explorer</h1><p>Inspect identity resolution, evidence provenance and connected relationships.</p></div><button className="glass-button" onClick={() => navigate("/graph")}>Open graph<ArrowRight size={16} /></button></div>
    <div className="entity-layout">
      <aside className="entity-list glass-card"><div className="entity-search"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search entities..." /></div>
        {loading ? <LoadingState label="Loading entities..." /> : error ? <ErrorState title="Entities are unavailable" action={() => window.location.reload()} /> : items.map((entity) => <button className={`entity-item ${selectedId === entity.id ? "active" : ""}`} key={entity.id} onClick={() => setSelectedId(entity.id)}><span className="entity-dot"><EntityIcon type={entity.entity_type} /></span><span><strong>{entity.name}</strong><small>{entity.entity_type} · Risk {entity.risk_score ?? "unassessed"}</small></span><b>{entity.risk_score ?? "—"}</b></button>)}
        {!loading && !error && items.length === 0 && <p className="empty-event">No entities have been recorded{query ? " for this search" : " yet"}.</p>}
      </aside>
      <main className="entity-detail glass-card">
        {detailLoading ? <LoadingState label="Loading entity details..." /> : selected ? <>
          <div className="entity-title"><div className="entity-big-icon"><EntityIcon type={selected.entity_type} /></div><div><span>{selected.entity_type}</span><h2>{selected.name}</h2><p>{selected.description || "No description has been recorded."}</p></div></div>
          <div className="entity-stats"><div><span>Resolution</span><strong>{(selected.resolution_status || "UNRESOLVED").replace(/_/g, " ")}</strong></div><div><span>Confidence</span><strong>{selected.resolution_confidence == null ? "—" : `${Math.round(selected.resolution_confidence * 100)}%`}</strong></div><div><span>Evidence</span><strong>{selected.evidence_count ?? 0}</strong></div></div>
          {!selected.resolution_status ? <p className="entity-resolution-notice">Identity resolution has not run; this entity’s canonical identity is unconfirmed.</p> : selected.resolution_status === "UNRESOLVED" || selected.resolution_status === "POSSIBLE_DUPLICATE" ? <p className="entity-resolution-notice">Entity identity could not be confidently resolved.</p> : <p className="entity-resolution-notice">Canonical name: <strong>{selected.canonical_entity_name || selected.name}</strong></p>}
          {selected.canonical_entity_id && selected.canonical_entity_id !== selected.id && <p className="entity-resolution-notice">Resolved alias of <strong>{selected.canonical_entity_name || selected.canonical_entity_id}</strong>.</p>}
          <div className="entity-stats"><div><span>Risk score</span><strong>{selected.risk_score ?? "—"}</strong></div><div><span>Connections</span><strong>{selected.connections.length}</strong></div><div><span>Jurisdiction</span><strong>{selected.jurisdiction || "—"}</strong></div></div>
          <div className="entity-section"><span className="drawer-label">IDENTIFIERS</span><div className="tag-row">{selected.identifiers.length ? selected.identifiers.map((identifier, index) => <span key={index}>{typeof identifier === "string" ? identifier : JSON.stringify(identifier)}</span>) : <span>No identifiers recorded</span>}</div></div>
          <div className="entity-section"><span className="drawer-label">ALIASES</span><div className="tag-row">{selected.aliases?.length ? selected.aliases.map((alias) => <span key={alias}>{alias}</span>) : <span>No aliases recorded</span>}</div></div>
          <div className="entity-section"><span className="drawer-label">SOURCES</span><div className="tag-row">{selected.sources?.length ? selected.sources.map((source) => <span key={source}>{source}</span>) : <span>No source provenance recorded</span>}</div></div>
          <div className="entity-section"><span className="drawer-label">RELATIONSHIPS</span><div className="relationship-cards">{selected.connections.length ? selected.connections.map((connection) => <button key={connection.id} onClick={() => navigate("/graph")}><strong>{connection.direction === "outgoing" ? `${selected.name} → ${connection.entity_name}` : `${connection.entity_name} → ${selected.name}`}</strong><span>{connection.relationship_type} · {connection.verification_status}<ArrowRight size={14} /></span></button>) : <p>No relationships have been recorded for this entity.</p>}<button onClick={() => navigate("/evidence")}><strong>Supporting evidence</strong><span>View recorded provenance<ArrowRight size={14} /></span></button></div></div>
        </> : <p className="empty-event">Select an entity to inspect its recorded details.</p>}
      </main>
    </div>
  </div>;
}
