import { useEffect, useMemo, useState } from "react";
import { Search, Star, Trash2 } from "lucide-react";
import { addToWatchlist, listWatchlist, removeFromWatchlist } from "../../features/watchlist/watchlist.api";
import { listEntities } from "../../features/entities/entity.api";
import type { Entity } from "../../types/entity.types";
import type { WatchlistItem } from "../../types/graph.types";
import { userMessage } from "../../services/api/errors";
import "./watchlist.css";

export default function Watchlist() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() { setError(""); setLoading(true); try { const [watchlist, entityRows] = await Promise.all([listWatchlist(), listEntities({ limit: 500 })]); setItems(watchlist); setEntities(entityRows); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, []);
  const names = useMemo(() => new Map(entities.map((entity) => [entity.id, entity])), [entities]);
  const filtered = items.filter((item) => (names.get(item.entity_id)?.name || item.name || "").toLowerCase().includes(query.toLowerCase()));
  const alreadyWatched = new Set(items.map((item) => item.entity_id));
  const addable = entities.filter((entity) => !alreadyWatched.has(entity.id));
  async function add() { if (!selectedId) return; try { await addToWatchlist(selectedId); setSelectedId(""); await load(); } catch (reason) { setError(userMessage(reason)); } }
  async function remove(entityId: string) { try { await removeFromWatchlist(entityId); setItems((current) => current.filter((item) => item.entity_id !== entityId)); } catch (reason) { setError(userMessage(reason)); } }
  return <main className="watchlist-page"><header className="watchlist-header"><div><span className="watchlist-eyebrow">MONITORED ENTITIES</span><h1>Watchlist</h1><p>Entities saved to your account for quick access.</p></div></header>
    {error && <p role="alert">{error} <button type="button" onClick={() => void load()}>Retry</button></p>}
    <section className="watchlist-container"><div className="watchlist-toolbar"><label className="watch-search"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search watched entities…" /></label><div><select aria-label="Entity to add" value={selectedId} onChange={(event) => setSelectedId(event.target.value)}><option value="">Choose an entity to watch</option>{addable.map((entity) => <option key={entity.id} value={entity.id}>{entity.name} · {entity.entity_type}</option>)}</select><button type="button" disabled={!selectedId} onClick={() => void add()}>Add entity</button></div></div>
      {loading ? <p aria-live="polite">Loading watchlist…</p> : filtered.length === 0 ? <div className="watch-empty"><Star size={26} /><h3>{items.length ? "No watched entities match" : "Your watchlist is empty"}</h3><p>Add an entity already recorded in the backend to begin monitoring it here.</p></div> : <div className="watchlist-list">{filtered.map((item) => { const entity = names.get(item.entity_id); return <article className="watch-card" key={item.id}><div className="watch-icon"><Star size={20} /></div><div className="watch-main"><span className="watch-type">{entity?.entity_type || "Entity"}</span><h3>{entity?.name || item.name || item.entity_id}</h3><p>{entity?.description || entity?.country || "No additional entity details."}</p><small>Added {new Date(item.created_at).toLocaleString()}</small></div><button type="button" className="watch-menu" aria-label={`Remove ${entity?.name || "entity"} from watchlist`} onClick={() => void remove(item.entity_id)}><Trash2 size={17} /></button></article>; })}</div>}
    </section></main>;
}
