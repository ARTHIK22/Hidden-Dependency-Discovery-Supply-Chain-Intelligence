import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ChevronRight, Factory, Globe2, Package, Search, ShieldAlert, Target, TrendingUp, X } from "lucide-react";
import { listRisks, getRiskSummary } from "../../features/risks/risk.api";
import { ErrorState, LoadingState } from "../../components/states/AsyncStates";
import type { Risk } from "../../types/api.types";
import "./risk.css";

type RiskLevel = "Critical" | "High" | "Medium" | "Low";
type RiskItem = Risk & { entity: string; type: string; levelLabel: RiskLevel };
const levels: RiskLevel[] = ["Critical", "High", "Medium", "Low"];

function RiskIntelligence() {
 const [items, setItems] = useState<RiskItem[]>([]);
 const [selected, setSelected] = useState<RiskItem | null>(null);
 const [search, setSearch] = useState("");
 const [level, setLevel] = useState<RiskLevel | "All">("All");
 const [summary, setSummary] = useState({ total: 0, high_risk: 0, average_score: 0 });
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState(false);

 useEffect(() => {
  const controller = new AbortController();
  Promise.all([listRisks(undefined, controller.signal), getRiskSummary(controller.signal)])
   .then(([riskList, summaryData]) => {
    setItems(riskList.items.map((risk) => ({ ...risk, entity: risk.entity_name, type: risk.entity_type, levelLabel: normalizeLevel(risk.level) })));
    setSummary(summaryData); setError(false);
   })
   .catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setError(true); } })
   .finally(() => { if (!controller.signal.aborted) setLoading(false); });
  return () => controller.abort();
 }, []);

 const filteredRisks = useMemo(() => items.filter((risk) =>
  (!search || `${risk.entity} ${risk.type}`.toLowerCase().includes(search.toLowerCase())) &&
  (level === "All" || risk.levelLabel === level)
 ), [items, search, level]);
 const criticalCount = items.filter((risk) => risk.levelLabel === "Critical").length;
 const distribution = levels.map((label) => ({ label, value: items.filter((item) => item.levelLabel === label).length }));

 return <div className="risk-page"><header className="risk-header"><div><div className="risk-eyebrow"><ShieldAlert size={14} />DEPENDENCY RISK INTELLIGENCE</div><h1>Risk Intelligence</h1><p>Review recorded risk assessments and their linked entities.</p></div><div className="risk-search"><Search size={17} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search risk entities..." /></div></header>
 <section className="risk-summary-grid"><SummaryCard label="Overall Risk" value={`${Math.round(summary.average_score)}`} suffix="/100" icon={<Target size={19} />} description="Average recorded assessment" /><SummaryCard label="Critical" value={`${criticalCount}`} icon={<AlertTriangle size={19} />} description="Critical assessments" danger /><SummaryCard label="High Risk" value={`${summary.high_risk}`} icon={<TrendingUp size={19} />} description="High or critical records" /><SummaryCard label="Risk Records" value={`${summary.total}`} icon={<ShieldAlert size={19} />} description="Persisted assessments" /></section>
 <div className="risk-content"><section className="risk-main glass-panel"><div className="risk-toolbar"><div><span className="risk-kicker">EXPOSURE ANALYSIS</span><h2>Dependency Risks</h2></div><div className="risk-filters">{(["All", ...levels] as const).map((item) => <button key={item} className={level === item ? "active" : ""} onClick={() => setLevel(item)}>{item}</button>)}</div></div>
 {loading ? <LoadingState label="Loading risk records..." /> : error ? <ErrorState title="Risk records are unavailable" action={() => window.location.reload()} /> : <div className="risk-table"><div className="risk-table-head"><span>Dependency</span><span>Risk</span><span>Score</span><span>Change</span><span>Investigation</span><span /></div>{filteredRisks.map((risk) => <button key={risk.id} className="risk-row" onClick={() => setSelected(risk)}><div className="risk-entity"><div className={`risk-entity-icon ${risk.levelLabel.toLowerCase()}`}>{getRiskIcon(risk.type)}</div><div><strong>{risk.entity}</strong><span>{risk.type}</span></div></div><RiskBadge level={risk.levelLabel} /><div className="risk-score"><strong>{Math.round(risk.score)}</strong><div className="score-track"><div className={`score-fill ${risk.levelLabel.toLowerCase()}`} style={{ width: `${Math.max(0, Math.min(100, risk.score))}%` }} /></div></div><div className="risk-change"><span>—</span></div><span className="risk-exposure">{risk.investigation_id ? risk.investigation_id.slice(0, 8) : "Workspace"}</span><ChevronRight size={16} /></button>)}{!filteredRisks.length && <p className="empty-event">{items.length ? "No risk records match these filters." : "No risk assessments have been recorded yet."}</p>}</div>}</section>
 <aside className="risk-overview glass-panel"><span className="risk-kicker">RISK DISTRIBUTION</span><h2>Exposure Map</h2><div className="risk-ring"><div className="risk-ring-inner"><strong>{Math.round(summary.average_score)}</strong><span>RISK INDEX</span></div></div><div className="distribution-list">{distribution.map((item) => <div className="distribution-row" key={item.label}><div><span className={`distribution-dot ${item.label.toLowerCase()}`} /><span>{item.label}</span></div><strong>{item.value}</strong></div>)}</div><div className="risk-insight"><AlertTriangle size={17} /><div><strong>Recorded assessments</strong><p>Risk results reflect persisted backend records; no risk inference is generated by this screen.</p></div></div></aside></div>
 {selected && <RiskDetail risk={selected} onClose={() => setSelected(null)} />}</div>;
}

function normalizeLevel(value: string): RiskLevel { const normalized = value.toLowerCase(); return levels.find((item) => item.toLowerCase() === normalized) ?? "Low"; }
function SummaryCard({ label, value, suffix, icon, description, danger }: { label: string; value: string; suffix?: string; icon: ReactNode; description: string; danger?: boolean }) { return <div className={`summary-card glass-panel ${danger ? "danger" : ""}`}><div className="summary-top"><span>{label}</span><div className="summary-icon">{icon}</div></div><div className="summary-value">{value}{suffix && <small>{suffix}</small>}</div><p>{description}</p></div>; }
function RiskBadge({ level }: { level: RiskLevel }) { return <span className={`risk-level ${level.toLowerCase()}`}><span />{level}</span>; }
function RiskDetail({ risk, onClose }: { risk: RiskItem; onClose: () => void }) { return <div className="risk-overlay" onClick={onClose}><aside className="risk-drawer" onClick={(event) => event.stopPropagation()}><div className="drawer-header"><div><span className="risk-kicker">RECORDED RISK</span><h2>{risk.entity}</h2></div><button onClick={onClose}><X size={17} /></button></div><RiskBadge level={risk.levelLabel} /><div className="drawer-score"><div><span>Risk score</span><strong>{Math.round(risk.score)}/100</strong></div><div className="large-score-track"><div className={`score-fill ${risk.levelLabel.toLowerCase()}`} style={{ width: `${Math.max(0, Math.min(100, risk.score))}%` }} /></div></div><section className="drawer-section"><span className="risk-kicker">ASSESSMENT REASON</span><p className="drawer-reason">{risk.reason}</p></section><section className="drawer-section"><span className="risk-kicker">ENTITY TYPE</span><div className="affected-card"><Package size={18} /><strong>{risk.type}</strong><ChevronRight size={15} /></div></section><section className="drawer-section"><span className="risk-kicker">RECORDED</span><p>{new Date(risk.created_at).toLocaleString()}</p></section></aside></div>; }
function getRiskIcon(type: string) { if (type.toLowerCase().includes("region")) return <Globe2 size={18} />; if (type.toLowerCase().includes("facility")) return <Factory size={18} />; return <Package size={18} />; }
export default RiskIntelligence;
