import { FormEvent, useEffect, useState } from "react";
import { Search } from "lucide-react";
import { createEntity, listEntities } from "../../features/entities/entity.api";
import type { Entity } from "../../types/entity.types";
import { userMessage } from "../../services/api/errors";
import "./entities.css";

export default function EntityList() {
  const [items, setItems] = useState<Entity[]>([]);
  const [query, setQuery] = useState("");
  const [name, setName] = useState("");
  const [entityType, setEntityType] = useState("company");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load(search = query) { setError(""); setLoading(true); try { setItems(await listEntities({ q: search || undefined, limit: 100, offset: 0 })); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }
  useEffect(() => { const timer = window.setTimeout(() => void load(query), 250); return () => window.clearTimeout(timer); }, [query]);
  async function submit(event: FormEvent) { event.preventDefault(); setError(""); try { await createEntity({ name, entity_type: entityType }); setName(""); await load(); } catch (reason) { setError(userMessage(reason)); } }
  return <main className="entities-page"><header><span className="eyebrow">ENTITY CATALOG</span><h1>Entities</h1><p>Organizations and other entities currently recorded in the backend.</p></header>{error && <p role="alert">{error} <button type="button" onClick={() => void load()}>Retry</button></p>}
    <form onSubmit={submit} className="entity-create-form"><label>Name<input required maxLength={500} value={name} onChange={(event) => setName(event.target.value)} /></label><label>Type<select value={entityType} onChange={(event) => setEntityType(event.target.value)}>{["company", "organization", "supplier", "manufacturer", "distributor", "facility", "location", "product", "component", "technology", "person", "government_entity", "unknown"].map((item) => <option key={item}>{item}</option>)}</select></label><button type="submit">Add entity</button></form>
    <label className="entity-search"><Search size={16} /><input aria-label="Search entities" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by name or alias…" /></label>
    {loading ? <p aria-live="polite">Loading entities…</p> : items.length === 0 ? <p>No entities found.</p> : <div className="entity-table"><div className="entity-table-head"><span>Name</span><span>Type</span><span>Country</span><span>Status</span></div>{items.map((entity) => <article className="entity-table-row" key={entity.id}><div><strong>{entity.name}</strong>{entity.canonical_name && entity.canonical_name !== entity.name && <small>Canonical: {entity.canonical_name}</small>}</div><span>{entity.entity_type}</span><span>{entity.country || "—"}</span><span>{entity.status}</span></article>)}</div>}
  </main>;
}
