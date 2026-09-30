import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { archiveInvestigation, listInvestigations, startInvestigation } from "../../features/investigations/investigation.api";
import type { Investigation } from "../../types/investigation.types";
import { userMessage } from "../../services/api/errors";

export default function InvestigationList() {
  const navigate = useNavigate();
  const [items, setItems] = useState<Investigation[]>([]);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState("");
  async function load() { setError(""); try { setItems(await listInvestigations({ limit: 20, offset })); } catch (reason) { setError(userMessage(reason)); } }
  useEffect(() => { void load(); }, [offset]);
  async function start(item: Investigation) { setBusyId(item.id); try { await startInvestigation(item.id); navigate(`/investigations/${item.id}`); } catch (reason) { setError(userMessage(reason)); } finally { setBusyId(""); } }
  async function archive(item: Investigation) { if (!window.confirm(`Archive “${item.name}”?`)) return; try { await archiveInvestigation(item.id); setItems((current) => current.filter((row) => row.id !== item.id)); } catch (reason) { setError(userMessage(reason)); } }
  return <main className="investigation-list-page"><header><span className="eyebrow">WORKSPACE</span><h1>Investigations</h1><p>Saved investigation records for your account.</p><Link to="/investigations/new">Create investigation</Link></header>{error && <p role="alert">{error} <button type="button" onClick={() => void load()}>Retry</button></p>}{items.length === 0 ? <p>No investigations on this page.</p> : items.map((item) => <article className="investigation-row" key={item.id}><button type="button" onClick={() => navigate(`/investigations/${item.id}`)}><strong>{item.name}</strong><span>{item.target || item.description || "No description"}</span><small>{item.status} · Updated {new Date(item.updated_at).toLocaleString()}</small></button><div>{["draft", "paused", "failed"].includes(item.status) && <button disabled={busyId === item.id} onClick={() => void start(item)}>{busyId === item.id ? "Starting…" : item.status === "draft" ? "Start" : "Resume"}</button>}<button onClick={() => void archive(item)}>Archive</button></div></article>)}<footer><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>Previous</button><button disabled={items.length < 20} onClick={() => setOffset(offset + 20)}>Next</button></footer></main>;
}
