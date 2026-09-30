import { useEffect, useMemo, useState } from "react";
import { ExternalLink, FileSearch, Search, ShieldCheck } from "lucide-react";
import { listEvidence } from "../../features/evidence/evidence.api";
import { listSources } from "../../features/sources/source.api";
import { listEntities } from "../../features/entities/entity.api";
import { listRelationships } from "../../features/relationships/relationship.api";
import type { Evidence } from "../../types/evidence.types";
import type { Source } from "../../types/source.types";
import type { Entity } from "../../types/entity.types";
import type { Relationship } from "../../types/relationship.types";
import { userMessage } from "../../services/api/errors";
import "./evidence.css";

export default function Evidence() {
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() { setLoading(true); setError(""); try { const [e, s, n, r] = await Promise.all([listEvidence({ limit: 500 }), listSources({ limit: 500 }), listEntities({ limit: 500 }), listRelationships({ limit: 500 })]); setEvidence(e); setSources(s); setEntities(n); setRelationships(r); if (e[0]) setSelectedId(e[0].id); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, []);
  const sourceMap = useMemo(() => new Map(sources.map((source) => [source.id, source])), [sources]);
  const entityMap = useMemo(() => new Map(entities.map((entity) => [entity.id, entity.name])), [entities]);
  const relationMap = useMemo(() => new Map(relationships.map((relation) => [relation.id, relation])), [relationships]);
  const filtered = evidence.filter((item) => [item.title, item.content, item.evidence_type].some((value) => value.toLowerCase().includes(search.toLowerCase())));
  const selected = evidence.find((item) => item.id === selectedId) || filtered[0];
  const selectedRelation = selected?.relationship_id ? relationMap.get(selected.relationship_id) : undefined;
  return <main className="evidence-page"><header className="evidence-header"><div><div className="evidence-eyebrow"><ShieldCheck size={14} />STORED EVIDENCE</div><h1>Evidence Explorer</h1><p>Evidence is shown from investigations you are allowed to access.</p></div><label className="evidence-search"><Search size={17} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search evidence…" /></label></header>
    {error && <p role="alert">{error} <button type="button" onClick={() => void load()}>Retry</button></p>}<div className="evidence-layout"><section className="relationship-panel glass-panel"><div className="panel-heading"><div><span className="panel-kicker">EVIDENCE RECORDS</span><h2>Results</h2></div><span className="count-pill">{filtered.length}</span></div>{loading ? <p aria-live="polite">Loading evidence…</p> : filtered.length === 0 ? <p>No matching evidence records.</p> : <div className="relationship-cards">{filtered.map((item) => <button key={item.id} className={`relationship-card ${item.id === selected?.id ? "selected" : ""}`} onClick={() => setSelectedId(item.id)}><strong>{item.title}</strong><p>{item.evidence_type} · {Math.round(item.confidence_score * 100)}% confidence</p><small>{new Date(item.collected_at).toLocaleString()}</small></button>)}</div>}</section>
      {selected && <section className="evidence-detail glass-panel"><span className="panel-kicker">EVIDENCE DETAIL</span><h2>{selected.title}</h2><p>{selected.content}</p><dl><dt>Type</dt><dd>{selected.evidence_type}</dd><dt>Confidence</dt><dd>{Math.round(selected.confidence_score * 100)}%</dd><dt>Verification</dt><dd>{selected.verification_status}</dd><dt>Collected</dt><dd>{new Date(selected.collected_at).toLocaleString()}</dd><dt>Published</dt><dd>{selected.published_at ? new Date(selected.published_at).toLocaleDateString() : "Not provided"}</dd><dt>Source</dt><dd>{selected.source_id ? sourceMap.get(selected.source_id)?.name || selected.source_id : "Not linked"}</dd><dt>Entity</dt><dd>{selected.entity_id ? entityMap.get(selected.entity_id) || selected.entity_id : "Not linked"}</dd><dt>Relationship</dt><dd>{selectedRelation ? `${selectedRelation.relationship_type} · ${entityMap.get(selectedRelation.source_entity_id) || "Entity"} → ${entityMap.get(selectedRelation.target_entity_id) || "Entity"}` : "Not linked"}</dd></dl>{selected.url && <a href={selected.url} target="_blank" rel="noreferrer">Open source reference <ExternalLink size={14} /></a>}{selected.content_hash && <small>SHA-256: {selected.content_hash}</small>}</section>}
      {!selected && !error && <p><FileSearch /> No evidence is stored yet.</p>}
    </div></main>;
}
