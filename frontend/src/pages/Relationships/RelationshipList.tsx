import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { listRelationships } from "../../features/relationships/relationship.api";
import type { RelationshipRecord } from "../../features/relationships/relationship.api";
import { userMessage } from "../../services/api/errors";
import "./relationships.css";

export default function RelationshipList() {
  const [items, setItems] = useState<RelationshipRecord[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() { setLoading(true); setError(""); try { setItems(await listRelationships()); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, []);
  const filtered = useMemo(() => items.filter((item) => `${item.relationship_type} ${item.source_entity_name} ${item.target_entity_name}`.toLowerCase().includes(query.toLowerCase())), [items, query]);
  return <main className="relationships-page"><header><span className="eyebrow">RECORDED CONNECTIONS</span><h1>Relationships</h1><p>Stored directed relationships, confidence and verification state.</p></header><label className="relationship-search"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search relationship or entity…" /></label>{error && <p role="alert">{error} <button type="button" onClick={() => void load()}>Retry</button></p>}{loading ? <p aria-live="polite">Loading relationships…</p> : filtered.length === 0 ? <p>No relationships recorded.</p> : <div className="relationship-table"><div className="relationship-table-head"><span>Source</span><span>Relationship</span><span>Target</span><span>Confidence score</span><span>Verification</span></div>{filtered.map((item) => <article className="relationship-table-row" key={item.id}><strong>{item.source_entity_name}</strong><span>{item.relationship_type}</span><strong>{item.target_entity_name}</strong><span>{item.confidence === null ? "—" : `${Math.round(item.confidence * 100)}%`}</span><span>{item.verification_status}</span></article>)}</div>}</main>;
}
