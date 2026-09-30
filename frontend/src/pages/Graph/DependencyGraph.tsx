import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Search, ShieldCheck } from "lucide-react";
import { exportGraph, getDependencyPath } from "../../features/exports/export.api";
import { getRiskAnalysis } from "../../features/risks/risk.api";
import type { GraphData } from "../../types/graph.types";
import { userMessage } from "../../services/api/errors";
import "./graph.css";

export default function DependencyGraph() {
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });
  const [riskyEntities, setRiskyEntities] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");
  const [riskOnly, setRiskOnly] = useState(false);
  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [path, setPath] = useState<string[] | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() { setLoading(true); setError(""); try { const [data, risk] = await Promise.all([exportGraph(), getRiskAnalysis()]); setGraph(data); setRiskyEntities(new Set(risk.risks.map((item) => item.entity_id))); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, []);
  const visibleNodes = useMemo(() => graph.nodes.filter((node) =>
    (!search || node.name.toLowerCase().includes(search.toLowerCase())) &&
    (!riskOnly || riskyEntities.has(node.id))), [graph.nodes, search, riskOnly, riskyEntities]);
  const shownIds = new Set(visibleNodes.map((node) => node.id));
  const visibleEdges = graph.edges.filter((edge) => shownIds.has(edge.source) && shownIds.has(edge.target));
  const coords = new Map(visibleNodes.map((node, index) => {
    const columns = Math.max(1, Math.ceil(Math.sqrt(visibleNodes.length)));
    return [node.id, { x: 110 + (index % columns) * Math.min(230, 780 / columns), y: 100 + Math.floor(index / columns) * 150 }];
  }));
  const height = Math.max(300, 170 * Math.ceil(visibleNodes.length / Math.max(1, Math.ceil(Math.sqrt(visibleNodes.length)))));
  async function findPath() {
    setError(""); setPath(null);
    try { const result = await getDependencyPath(sourceId, targetId); setPath(result.path); }
    catch (reason) { setError(userMessage(reason)); }
  }
  return <main className="graph-page"><header className="graph-header"><div><div className="graph-eyebrow">RECORDED DEPENDENCIES</div><h1>Dependency Graph</h1><p>Relationships currently recorded in the backend.</p></div><div className="graph-header-actions"><label className="graph-search"><Search size={17} /><input aria-label="Search entities" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search entities…" /></label><button className={`filter-chip ${riskOnly ? "selected" : ""}`} onClick={() => setRiskOnly((value) => !value)}><AlertTriangle size={14} />Risk entities</button></div></header>
    {error && <p role="alert" className="auth-error">{error} <button type="button" onClick={() => void load()}>Retry</button></p>}
    <section className="graph-layout"><div className="graph-canvas glass-panel"><div className="canvas-toolbar"><strong>{visibleNodes.length} entities · {visibleEdges.length} relationships</strong></div>{loading ? <p aria-live="polite">Loading graph…</p> : visibleNodes.length === 0 ? <p>No recorded graph data matches this view.</p> : <svg className="dependency-svg" viewBox={`0 0 1000 ${height}`} role="img" aria-label="Recorded entity relationship graph"><defs><marker id="api-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#a97858" /></marker></defs>{visibleEdges.map((edge) => { const a = coords.get(edge.source); const b = coords.get(edge.target); if (!a || !b) return null; const highlighted = path?.includes(edge.source) && path?.includes(edge.target); return <g key={edge.id} className={`graph-edge ${highlighted ? "selected-edge" : ""}`}><line x1={a.x} y1={a.y} x2={b.x} y2={b.y} markerEnd="url(#api-arrow)" /><text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 8} textAnchor="middle">{edge.type} · {Math.round(edge.confidence * 100)}%</text></g>; })}{visibleNodes.map((node) => { const p = coords.get(node.id)!; return <g key={node.id} className="graph-node" transform={`translate(${p.x},${p.y})`}><circle className={`node-circle ${riskyEntities.has(node.id) ? "node-risk" : "node-company"}`} r="35" /><text className="node-label" y="58" textAnchor="middle">{node.name.length > 26 ? `${node.name.slice(0, 23)}…` : node.name}</text><text y="4" textAnchor="middle">{node.type}</text>{riskyEntities.has(node.id) && <ShieldCheck className="risk-dot" />}</g>; })}</svg>}</div>
    <aside className="glass-panel graph-path-panel"><h2>Dependency path</h2><p>Find a shortest path through recorded relationships.</p><label>From<select value={sourceId} onChange={(event) => setSourceId(event.target.value)}><option value="">Select entity</option>{graph.nodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select></label><label>To<select value={targetId} onChange={(event) => setTargetId(event.target.value)}><option value="">Select entity</option>{graph.nodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select></label><button disabled={!sourceId || !targetId || sourceId === targetId} onClick={() => void findPath()}>Find path</button>{path && <ol>{path.map((id) => <li key={id}>{graph.nodes.find((node) => node.id === id)?.name || id}</li>)}</ol>}</aside></section>
  </main>;
}
