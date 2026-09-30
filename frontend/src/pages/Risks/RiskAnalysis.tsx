import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, RefreshCw, ShieldAlert } from "lucide-react";
import { getRiskSummary, listRisks } from "../../features/risks/risk.api";
import { userMessage } from "../../services/api/errors";
import type { Risk } from "../../types/api.types";
import "./risk.css";

export default function RiskAnalysis() {
  const [risks, setRisks] = useState<Risk[]>([]);
  const [riskTotal, setRiskTotal] = useState(0);
  const [summary, setSummary] = useState<{ total: number; high_risk: number; average_score: number } | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() { setLoading(true); setError(""); try { const [riskList, riskSummary] = await Promise.all([listRisks(), getRiskSummary()]); setRisks(riskList.items); setRiskTotal(riskList.total); setSummary(riskSummary); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, []);
  const filteredRisks = useMemo(() => risks.filter((risk) => `${risk.entity_name} ${risk.entity_type} ${risk.level} ${risk.reason}`.toLowerCase().includes(query.toLowerCase())), [risks, query]);
  return <main className="risk-page"><header className="risk-header"><div><div className="risk-eyebrow"><ShieldAlert size={14} />RECORDED DEPENDENCY RISK</div><h1>Risk Intelligence</h1><p>Review persisted risk records and the reasons supplied by the backend.</p></div><div className="risk-search"><input aria-label="Search risks" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search risk records…" /><button onClick={() => void load()}><RefreshCw size={15} />Refresh</button></div></header>
    {error && <p role="alert">{error}</p>}{loading ? <p>Loading recorded risk data…</p> : <><section className="risk-summary-grid"><Summary label="Risk records" value={String(summary?.total ?? 0)} /><Summary label="High or critical" value={String(summary?.high_risk ?? 0)} /><Summary label="Average score" value={String(summary?.average_score ?? 0)} /></section><section className="risk-main glass-panel"><header><h2>Dependency risks</h2><span>{filteredRisks.length} shown · {riskTotal} in this list</span></header>{filteredRisks.length === 0 ? <p>No risk records are available for the current data.</p> : filteredRisks.map((risk) => <article className="risk-row" key={risk.id}><div><span className={`risk-level ${risk.level.toLowerCase()}`}>{risk.level}</span><h3>{risk.entity_type.split("_").join(" ")}</h3><strong>{risk.entity_name}</strong><p>{risk.reason}</p></div><div className="risk-score"><strong>{risk.score}</strong><small>stored score</small></div></article>)}</section><p><AlertTriangle size={14} /> Risk scores and explanations are returned from persisted backend records.</p></>}
  </main>;
}
function Summary({ label, value }: { label: string; value: string }) { return <article className="summary-card glass-panel"><span>{label}</span><strong>{value}</strong></article>; }
