import { FormEvent, useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { createSource, listSources } from "../../features/sources/source.api";
import type { Source } from "../../types/source.types";
import { userMessage } from "../../services/api/errors";
import "./sources.css";

export default function SourceList() {
  const [items, setItems] = useState<Source[]>([]);
  const [name, setName] = useState("");
  const [sourceType, setSourceType] = useState("manual");
  const [url, setUrl] = useState("");
  const [reliability, setReliability] = useState("0.5");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() { setError(""); setLoading(true); try { setItems(await listSources({ limit: 500 })); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, []);
  async function submit(event: FormEvent) { event.preventDefault(); setError(""); try { await createSource({ name, source_type: sourceType, url: url || null, reliability_score: Number(reliability) }); setName(""); setUrl(""); await load(); } catch (reason) { setError(userMessage(reason)); } }
  return <main className="sources-page"><header><span className="eyebrow">SOURCE CATALOG</span><h1>Sources</h1><p>Registered source metadata and reliability values. URLs are references; the backend does not fetch them.</p></header>{error && <p role="alert">{error} <button type="button" onClick={() => void load()}>Retry</button></p>}
    <form onSubmit={submit} className="source-create-form"><label>Name<input required value={name} onChange={(event) => setName(event.target.value)} /></label><label>Type<input required value={sourceType} onChange={(event) => setSourceType(event.target.value)} /></label><label>URL<input type="url" value={url} onChange={(event) => setUrl(event.target.value)} /></label><label>Reliability (0–1)<input type="number" min="0" max="1" step="0.01" value={reliability} onChange={(event) => setReliability(event.target.value)} /></label><button type="submit">Register source</button></form>
    {loading ? <p aria-live="polite">Loading sources…</p> : items.length === 0 ? <p>No sources registered.</p> : <div className="source-list">{items.map((source) => <article className="source-card" key={source.id}><div className="source-content"><span className="source-type">{source.source_type}</span><h2>{source.name}</h2><p>{source.publisher || source.description || "No additional metadata."}</p><span>Reliability {Math.round(source.reliability_score * 100)}%</span>{source.url && <a href={source.url} target="_blank" rel="noreferrer">Open reference <ExternalLink size={14} /></a>}</div></article>)}</div>}
  </main>;
}
