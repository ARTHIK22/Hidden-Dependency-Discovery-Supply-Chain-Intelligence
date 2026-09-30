import { useEffect, useMemo, useState } from "react";
import { Building2, ChevronRight, Factory, Globe2, MoreHorizontal, Package, Plus, Search, Star, TrendingUp, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { addToWatchlist, listEntities, listWatchlist, removeFromWatchlist } from "../../features/entities/entity.api";
import { useToast } from "../../components/toast/ToastProvider";
import { ErrorState, LoadingState } from "../../components/states/AsyncStates";
import type { Entity, WatchlistEntry } from "../../types/api.types";
import "./watchlist.css";

const iconFor = (type: string) => {
  const normalized = type.toLowerCase();
  if (normalized.includes("material")) return Package;
  if (normalized.includes("facility") || normalized.includes("manufacturer")) return Factory;
  if (normalized.includes("region")) return Globe2;
  return Building2;
};

export default function Watchlist() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [items, setItems] = useState<WatchlistEntry[]>([]);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("All");
  const [addOpen, setAddOpen] = useState(false);
  const [addQuery, setAddQuery] = useState("");
  const [candidates, setCandidates] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const refresh = (signal?: AbortSignal) => listWatchlist(undefined, signal).then(({ items: rows }) => setItems(rows));
  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal).then(() => setError(false)).catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setError(true); } }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!addOpen) return;
    const controller = new AbortController();
    listEntities(addQuery || undefined, controller.signal)
      .then(({ items: rows }) => setCandidates(rows.filter((entity) => !items.some((watch) => watch.entity_id === entity.id))))
      .catch((cause) => { if (!controller.signal.aborted) console.error(cause); });
    return () => controller.abort();
  }, [addOpen, addQuery, items]);

  const filteredItems = useMemo(() => items.filter((item) => {
    const type = titleCase(item.entity_type);
    return `${item.entity_name} ${type}`.toLowerCase().includes(query.toLowerCase()) && (filter === "All" || item.entity_type.toLowerCase().includes(filter.toLowerCase()));
  }), [items, query, filter]);
  const withRisk = items.filter((item) => item.risk_score !== null).length;
  const elevated = items.filter((item) => ["critical", "high"].includes((item.risk_level || "").toLowerCase())).length;

  const addEntity = async (entity: Entity) => {
    setBusyId(entity.id);
    try {
      const entry = await addToWatchlist(entity.id);
      setItems((current) => [entry, ...current]);
      toast.success(`${entity.name} added to watchlist.`);
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : "Unable to add this entity.");
    } finally { setBusyId(null); }
  };

  const removeEntity = async (item: WatchlistEntry) => {
    setBusyId(item.entity_id);
    try {
      await removeFromWatchlist(item.entity_id);
      setItems((current) => current.filter((entry) => entry.entity_id !== item.entity_id));
      toast.success(`${item.entity_name} removed from watchlist.`);
    } catch (cause) { toast.error(cause instanceof Error ? cause.message : "Unable to remove this entity."); }
    finally { setBusyId(null); }
  };

  return <div className="watchlist-page">
    <section className="watchlist-header"><div><span className="watchlist-eyebrow">CONTINUOUS MONITORING</span><h1>Watchlist</h1><p>Keep recorded entities in a persistent watchlist for review.</p></div><button className="add-watch-button" onClick={() => setAddOpen((open) => !open)}><Plus size={17} />{addOpen ? "Close" : "Add to Watchlist"}</button></section>
    {addOpen && <section className="watch-add-panel glass-card"><div className="watch-search"><Search size={17} /><input value={addQuery} onChange={(event) => setAddQuery(event.target.value)} placeholder="Search existing entities..." /><button onClick={() => setAddOpen(false)} type="button" aria-label="Close"><X size={15} /></button></div><div className="watch-candidates">{candidates.map((entity) => <button key={entity.id} onClick={() => void addEntity(entity)} disabled={busyId === entity.id}><span>{entity.name} · {entity.entity_type}</span><strong>{busyId === entity.id ? "Adding..." : "Add"}</strong></button>)}{!candidates.length && <p>No unlisted entities found.</p>}</div></section>}
    <section className="watchlist-summary"><Summary icon={<Star size={20} />} value={items.length} label="Watched Items" /><Summary icon={<TrendingUp size={20} />} value={elevated} label="High or Critical Risk" critical /><Summary icon={<Building2 size={20} />} value={withRisk} label="With Risk Scores" /></section>
    <section className="watchlist-container"><div className="watchlist-toolbar"><div className="watch-search"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search watchlist..." />{query && <button onClick={() => setQuery("")} type="button"><X size={15} /></button>}</div><div className="watch-filters">{["All", "Supplier", "Material", "Facility", "Region"].map((item) => <button key={item} className={filter === item ? "active" : ""} onClick={() => setFilter(item)} type="button">{item}</button>)}</div></div>
      {loading ? <LoadingState label="Loading watchlist..." /> : error ? <ErrorState title="Watchlist is unavailable" description="Check the backend and PostgreSQL connection." action={() => window.location.reload()} /> : <div className="watchlist-list">{filteredItems.map((item) => { const Icon = iconFor(item.entity_type); const level = item.risk_level || "Unassessed"; return <article className="watch-card" key={item.id}><div className="watch-icon"><Icon size={21} /></div><div className="watch-main"><div className="watch-title-row"><div><span className="watch-type">{titleCase(item.entity_type)}</span><h3>{item.entity_name}</h3></div><button className="watch-menu" type="button" aria-label={`Remove ${item.entity_name}`} onClick={() => void removeEntity(item)} disabled={busyId === item.entity_id}><MoreHorizontal size={18} /></button></div><p>Watch status: {item.status}</p><div className="watch-meta"><span>Added {new Date(item.created_at).toLocaleDateString()}</span><span className="watch-dot">•</span><span>{item.risk_score === null ? "No risk change data" : `Risk score ${Math.round(item.risk_score)}`}</span></div></div><div className="watch-risk"><span className={`risk-badge ${level.toLowerCase()}`}>{level}</span><div className="risk-score"><strong>{item.risk_score === null ? "—" : Math.round(item.risk_score)}</strong><span>/100</span></div></div><button className="watch-open" type="button" aria-label="Open entities" onClick={() => navigate("/entities")}><ChevronRight size={18} /></button></article>; })}{!filteredItems.length && <div className="watch-empty"><Star size={26} /><h3>No watched items found</h3><p>{items.length ? "Try another search or filter." : "Add a recorded entity to start your watchlist."}</p></div>}</div>}
    </section>
  </div>;
}

function Summary({ icon, value, label, critical = false }: { icon: React.ReactNode; value: number; label: string; critical?: boolean }) { return <div className="watch-summary-card"><div className={`watch-summary-icon ${critical ? "critical" : ""}`}>{icon}</div><div><strong>{value}</strong><span>{label}</span></div></div>; }
function titleCase(value: string) { return value.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase()); }
