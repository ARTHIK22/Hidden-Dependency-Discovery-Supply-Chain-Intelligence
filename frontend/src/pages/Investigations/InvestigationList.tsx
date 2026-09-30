import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listInvestigations } from "../../features/investigations/investigation.api";
import type { Investigation } from "../../types/api.types";
import { userMessage } from "../../services/api/errors";

export default function InvestigationList() {
  const navigate = useNavigate();
  const [items, setItems] = useState<Investigation[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() { setError(""); setLoading(true); try { const response = await listInvestigations({ limit: 20, offset }); setItems(response.items); setTotal(response.total); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, [offset]);
  return <main className="investigation-list-page"><header><span className="eyebrow">WORKSPACE</span><h1>Investigations</h1><p>Saved investigation records. Queued records are persisted, but no worker is configured to run them.</p><Link to="/investigations/new">Create investigation</Link></header>{error && <p role="alert">{error} <button type="button" onClick={() => void load()}>Retry</button></p>}{loading ? <p aria-live="polite">Loading investigations…</p> : items.length === 0 ? <p>No investigations on this page.</p> : items.map((item) => <article className="investigation-row" key={item.id}><button type="button" onClick={() => navigate(`/investigations/${item.id}`)}><strong>{item.name}</strong><span>{item.goal}</span><small>{item.status} · {item.progress}% · Updated {new Date(item.updated_at).toLocaleString()}</small></button></article>)}<footer><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>Previous</button><span>{total} investigations</span><button disabled={offset + items.length >= total} onClick={() => setOffset(offset + 20)}>Next</button></footer></main>;
}
