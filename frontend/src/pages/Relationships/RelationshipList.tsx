import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { listRelationships } from "../../features/relationships/relationship.api";
import { listEntities } from "../../features/entities/entity.api";
import type { Entity } from "../../types/entity.types";
import type { Relationship } from "../../types/relationship.types";
import { userMessage } from "../../services/api/errors";
import "./relationships.css";

export default function RelationshipList() {
  const [items, setItems] = useState<Relationship[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() { setLoading(true); setError(""); try { const [rels, nodes] = await Promise.all([listRelationships({ limit: 500 }), listEntities({ limit: 500 })]); setItems(rels); setEntities(nodes); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, []);
  const names = useMemo(() => new Map(entities.map((entity) => [entity.id, entity.name])), [entities]);
  const filtered = items.filter((item) => `${item.relationship_type} ${names.get(item.source_entity_id) || ""} ${names.get(item.target_entity_id) || ""}`.toLowerCase().includes(query.toLowerCase()));
  return <main className="relationships-page"><header><span className="eyebrow">RECORDED CONNECTIONS</span><h1>Relationships</h1><p>Stored directed relationships, confidence and verification state.</p></header><label className="relationship-search"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search relationship or entity…" /></label>{error && <p role="alert">{error} <button type="button" onClick={() => void load()}>Retry</button></p>}{loading ? <p aria-live="polite">Loading relationships…</p> : filtered.length === 0 ? <p>No relationships recorded.</p> : <div className="relationship-table"><div className="relationship-table-head"><span>Source</span><span>Relationship</span><span>Target</span><span>Confidence</span><span>Verification</span></div>{filtered.map((item) => <article className="relationship-table-row" key={item.id}><strong>{names.get(item.source_entity_id) || item.source_entity_id}</strong><span>{item.relationship_type}</span><strong>{names.get(item.target_entity_id) || item.target_entity_id}</strong><span>{Math.round(item.confidence_score * 100)}%</span><span>{item.verification_status}</span></article>)}</div>}</main>;
}
