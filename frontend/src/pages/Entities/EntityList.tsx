import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { listEntities } from "../../features/entities/entity.api";
import type { Entity } from "../../types/api.types";
import { userMessage } from "../../services/api/errors";
import "./entities.css";

export default function EntityList() {
  const [items, setItems] = useState<Entity[]>([]);
  const [query, setQuery] = useState("");
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load(search = query, pageOffset = offset) { setError(""); setLoading(true); try { const response = await listEntities({ q: search || undefined, limit: 100, offset: pageOffset }); setItems(response.items); setTotal(response.total); setOffset(pageOffset); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }
  useEffect(() => { const timer = window.setTimeout(() => void load(query, 0), 250); return () => window.clearTimeout(timer); }, [query]);
  return <main className="entities-page"><header><span className="eyebrow">ENTITY CATALOG</span><h1>Entities</h1><p>Organizations and other entities currently recorded in the backend.</p></header>{error && <p role="alert">{error} <button type="button" onClick={() => void load()}>Retry</button></p>}
    <label className="entity-search"><Search size={16} /><input aria-label="Search entities" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by name or alias…" /></label>
    {loading ? <p aria-live="polite">Loading entities…</p> : items.length === 0 ? <p>No entities found.</p> : <div className="entity-table"><div className="entity-table-head"><span>Name</span><span>Type</span><span>Jurisdiction</span><span>Risk</span></div>{items.map((entity) => <article className="entity-table-row" key={entity.id}><div><strong>{entity.name}</strong>{entity.description && <small>{entity.description}</small>}</div><span>{entity.entity_type}</span><span>{entity.jurisdiction || "—"}</span><span>{entity.risk_level || "Unassessed"}</span></article>)}</div>}
    {!loading && !error && total > 0 && <footer><span>Showing {offset + 1}–{Math.min(offset + items.length, total)} of {total} entities</span><button type="button" disabled={offset === 0} onClick={() => void load(query, Math.max(0, offset - 100))}>Previous</button><button type="button" disabled={offset + items.length >= total} onClick={() => void load(query, offset + 100)}>Next</button></footer>}
  </main>;
}
