import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, RefreshCw, ShieldAlert } from "lucide-react";
import { getRiskAnalysis } from "../../features/risks/risk.api";
import { userMessage } from "../../services/api/errors";
import type { RiskAnalysis as RiskAnalysisData } from "../../types/risk.types";
import "./risk.css";

export default function RiskAnalysis() {
  const [analysis, setAnalysis] = useState<RiskAnalysisData | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() { setLoading(true); setError(""); try { setAnalysis(await getRiskAnalysis()); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, []);
  const risks = useMemo(() => (analysis?.risks || []).filter((risk) => `${risk.entity_name || risk.entity_id} ${risk.category} ${risk.explanation}`.toLowerCase().includes(query.toLowerCase())), [analysis, query]);
  return <main className="risk-page"><header className="risk-header"><div><div className="risk-eyebrow"><ShieldAlert size={14} />RECORDED DEPENDENCY RISK</div><h1>Risk Intelligence</h1><p>Structural risk signals calculated from recorded relationship data. These are not external threat-intelligence scores.</p></div><div className="risk-search"><input aria-label="Search risks" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search risk signals…" /><button onClick={() => void load()}><RefreshCw size={15} />Refresh</button></div></header>
    {error && <p role="alert">{error}</p>}{loading ? <p>Analyzing recorded relationships…</p> : <><section className="risk-summary-grid"><Summary label="Risk signals" value={String(analysis?.risks.length ?? 0)} /><Summary label="High severity" value={String((analysis?.risks || []).filter((risk) => risk.severity === "high" || risk.severity === "critical").length)} /><Summary label="Analysis basis" value={analysis?.basis || "Stored data"} /></section><section className="risk-main glass-panel"><header><h2>Dependency risks</h2><span>{risks.length} signals</span></header>{risks.length === 0 ? <p>No structural risk signals are available for the current data.</p> : risks.map((risk, index) => <article className="risk-row" key={`${risk.category}-${risk.entity_id}-${index}`}><div><span className={`risk-level ${risk.severity}`}>{risk.severity}</span><h3>{risk.category.split("_").join(" ")}</h3><strong>{risk.entity_name || risk.entity_id}</strong><p>{risk.explanation}</p></div><div className="risk-score"><strong>{Math.round(risk.score * 100)}%</strong><small>heuristic signal</small></div><small>Affected: {risk.affected_entities.length}</small></article>)}</section><p><AlertTriangle size={14} /> Backend response basis: {analysis?.basis}; external feeds: {analysis?.external_risk_feeds_used ? "used" : "not used"}.</p></>}
  </main>;
}
function Summary({ label, value }: { label: string; value: string }) { return <article className="summary-card glass-panel"><span>{label}</span><strong>{value}</strong></article>; }
