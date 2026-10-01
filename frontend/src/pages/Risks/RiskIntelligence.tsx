import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, ChevronRight, Factory, Globe2, Package, Search, ShieldAlert, Target, TrendingUp, X } from "lucide-react";
import { ErrorState, LoadingState } from "../../components/states/AsyncStates";
import { listInvestigations } from "../../features/investigations/investigation.api";
import {
  analyzeRisk,
  getInvestigationRiskSummary,
  getInvestigationRisks,
  getRiskAnalysisState,
  getRiskSummary,
  listRisks,
  type RiskAnalysisState,
} from "../../features/risks/risk.api";
import type { Investigation, Risk, RiskFactor } from "../../types/api.types";
import "./risk.css";

type RiskLevel = "Critical" | "High" | "Medium" | "Low" | "Unknown";
type RiskItem = Risk & { entity: string; type: string; levelLabel: RiskLevel };
type RiskSummary = { total: number; high_risk: number; average_score: number; unknown?: number };
type InvestigationRiskSummary = Record<string, unknown>;
const levels: RiskLevel[] = ["Critical", "High", "Medium", "Low", "Unknown"];

function RiskIntelligence() {
  const [items, setItems] = useState<RiskItem[]>([]);
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [selected, setSelected] = useState<RiskItem | null>(null);
  const [search, setSearch] = useState("");
  const [level, setLevel] = useState<RiskLevel | "All">("All");
  const [summary, setSummary] = useState<RiskSummary>({ total: 0, high_risk: 0, average_score: 0 });
  const [investigationSummary, setInvestigationSummary] = useState<InvestigationRiskSummary | null>(null);
  const [analysisState, setAnalysisState] = useState<RiskAnalysisState | null>(null);
  const [selectedInvestigationId, setSelectedInvestigationId] = useState("");
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([listInvestigations(undefined, controller.signal), getRiskSummary(controller.signal)])
      .then(([investigationList, summaryData]) => {
        setInvestigations(investigationList.items);
        setSummary(summaryData);
        const initial = investigationList.items.find((item) => item.status === "RISK_ANALYZED" || item.status === "COMPLETED")
          ?? investigationList.items[0];
        setSelectedInvestigationId(initial?.id ?? "");
        setError(false);
      })
      .catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setError(true); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  const reloadCurrent = useCallback(async (signal?: AbortSignal) => {
    const [riskList, riskSummary, analysis] = await Promise.all([
      getInvestigationRisks(selectedInvestigationId, signal),
      getInvestigationRiskSummary(selectedInvestigationId, signal),
      getRiskAnalysisState(selectedInvestigationId, signal),
    ]);
    setItems(riskList.items.map((risk) => ({ ...risk, entity: risk.entity_name, type: risk.entity_type, levelLabel: normalizeLevel(risk.level) })));
    setInvestigationSummary(riskSummary);
    setAnalysisState(analysis);
  }, [selectedInvestigationId]);

  useEffect(() => {
    if (!selectedInvestigationId) {
      const controller = new AbortController();
      listRisks(undefined, controller.signal)
        .then((riskList) => setItems(riskList.items.map((risk) => ({ ...risk, entity: risk.entity_name, type: risk.entity_type, levelLabel: normalizeLevel(risk.level) }))))
        .catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setError(true); } });
      return () => controller.abort();
    }
    const controller = new AbortController();
    reloadCurrent(controller.signal)
      .then(() => setError(false))
      .catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setError(true); } });
    return () => controller.abort();
  }, [selectedInvestigationId, reloadCurrent]);

  const selectedInvestigation = investigations.find((item) => item.id === selectedInvestigationId);
  const filteredRisks = useMemo(() => items.filter((risk) =>
    (!search || `${risk.entity} ${risk.type}`.toLowerCase().includes(search.toLowerCase())) &&
    (level === "All" || risk.levelLabel === level)
  ), [items, search, level]);
  const criticalCount = items.filter((risk) => risk.levelLabel === "Critical").length;
  const distribution = levels.slice(0, 4).map((label) => ({ label, value: items.filter((item) => item.levelLabel === label).length }));
  const overallScore = asNumber(investigationSummary?.overall_score) ?? summary.average_score;
  const canAnalyze = Boolean(selectedInvestigation && !selectedInvestigation.demo_mode && ["VERIFICATION_COMPLETED", "RISK_ANALYZED", "COMPLETED"].includes(selectedInvestigation.status));

  const runAnalysis = async () => {
    if (!selectedInvestigationId || !canAnalyze || analyzing) return;
    setAnalyzing(true);
    try {
      let current = await analyzeRisk(selectedInvestigationId);
      setAnalysisState(current);
      let attempts = 0;
      while (current.status === "RISK_ANALYZING" && attempts < 240) {
        await new Promise<void>((resolve) => window.setTimeout(resolve, 500));
        current = await getRiskAnalysisState(selectedInvestigationId);
        setAnalysisState(current);
        attempts += 1;
      }
      if (current.status === "FAILED") throw new Error(current.error_message || "Risk analysis failed.");
      const [riskList, riskSummary, refreshed] = await Promise.all([
        getInvestigationRisks(selectedInvestigationId),
        getInvestigationRiskSummary(selectedInvestigationId),
        getRiskAnalysisState(selectedInvestigationId),
      ]);
      setItems(riskList.items.map((risk) => ({ ...risk, entity: risk.entity_name, type: risk.entity_type, levelLabel: normalizeLevel(risk.level) })));
      setInvestigationSummary(riskSummary);
      setAnalysisState(refreshed);
      setSummary(await getRiskSummary());
      setInvestigations((previous) => previous.map((item) => item.id === selectedInvestigationId ? { ...item, status: "RISK_ANALYZED" } : item));
    } catch (cause) {
      console.error(cause);
      setError(true);
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) return <LoadingState label="Loading risk intelligence..." />;
  if (error) return <ErrorState title="Risk intelligence is unavailable" description="Check the backend and investigation access." action={() => window.location.reload()} />;

  return <div className="risk-page">
    <header className="risk-header"><div><div className="risk-eyebrow"><ShieldAlert size={14} />DEPENDENCY RISK INTELLIGENCE</div><h1>Risk Intelligence</h1><p>Scores use verified graph relationships and source-backed factors; missing inputs stay unknown.</p></div><div className="risk-search"><Search size={17} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search risk entities..." /></div></header>
    <div className="risk-analysis-controls"><select aria-label="Investigation for risk analysis" value={selectedInvestigationId} onChange={(event) => setSelectedInvestigationId(event.target.value)}><option value="">All visible investigations</option>{investigations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button className="risk-analyze-button" type="button" onClick={() => void runAnalysis()} disabled={!canAnalyze || analyzing}>{analyzing || analysisState?.status === "RISK_ANALYZING" ? "Analyzing risk…" : "Analyze Risk"}</button><span>{selectedInvestigation?.status ?? "Select an investigation"}</span></div>
    {selectedInvestigation?.demo_mode && <p className="risk-demo-notice">DEMO ONLY — these records are fictional interface fixtures. They are not calculated real-world risk findings.</p>}
    {analysisState?.status === "RISK_ANALYZING" && <div className="risk-progress-banner" role="status">{String(analysisState.risk_progress?.message ?? "Risk analysis is running…")}</div>}
    <section className="risk-summary-grid"><SummaryCard label="Overall Risk" value={overallScore == null ? "UNKNOWN" : `${Math.round(overallScore)}`} suffix={overallScore == null ? undefined : "/100"} icon={<Target size={19} />} description={selectedInvestigation ? "Calculated for selected investigation" : "Average visible assessment"} /><SummaryCard label="Critical" value={`${criticalCount}`} icon={<AlertTriangle size={19} />} description="Assessments at or above 75" danger /><SummaryCard label="High Risk" value={`${selectedInvestigation ? items.filter((item) => item.score !== null && item.score >= 50).length : summary.high_risk}`} icon={<TrendingUp size={19} />} description="Assessments at or above 50" /><SummaryCard label="Unknown" value={`${asNumber(investigationSummary?.unknown_factor_count) ?? summary.unknown ?? 0}`} icon={<ShieldAlert size={19} />} description="Factors without source-backed inputs" /></section>
    <div className="risk-content"><section className="risk-main glass-panel"><div className="risk-toolbar"><div><span className="risk-kicker">EXPOSURE ANALYSIS</span><h2>Dependency Risks</h2></div><div className="risk-filters">{(["All", ...levels] as const).map((item) => <button key={item} className={level === item ? "active" : ""} onClick={() => setLevel(item)} type="button">{item}</button>)}</div></div>
      <div className="risk-table"><div className="risk-table-head"><span>Dependency</span><span>Risk</span><span>Score</span><span>Factors</span><span>Investigation</span><span /></div>{filteredRisks.map((risk) => <button key={risk.id} className="risk-row" onClick={() => setSelected(risk)} type="button"><div className="risk-entity"><div className={`risk-entity-icon ${risk.levelLabel.toLowerCase()}`}>{getRiskIcon(risk.type)}</div><div><strong>{risk.entity}</strong><span>{risk.type}{risk.demo_mode ? " · DEMO" : ""}</span></div></div><RiskBadge level={risk.levelLabel} /><div className="risk-score"><strong>{risk.score === null ? "UNKNOWN" : Math.round(risk.score)}</strong><div className="score-track"><div className={`score-fill ${risk.levelLabel.toLowerCase()}`} style={{ width: `${Math.max(0, Math.min(100, risk.score ?? 0))}%` }} /></div></div><span>{risk.risk_factors?.filter((factor) => factor.status === "KNOWN").length ?? 0} known · {risk.risk_factors?.filter((factor) => factor.status === "UNKNOWN").length ?? 0} unknown</span><span className="risk-exposure">{risk.investigation_id ? risk.investigation_id.slice(0, 8) : "Workspace"}</span><ChevronRight size={16} /></button>)}{!filteredRisks.length && <p className="empty-event">{items.length ? "No risk records match these filters." : analysisState?.status === "RISK_ANALYZED" ? "No source-backed risk scores were available; unknown factors remain in the saved snapshot." : "No risk assessments have been recorded yet. Complete verification, then analyze an investigation."}</p>}</div>
    </section><aside className="risk-overview glass-panel"><span className="risk-kicker">RISK DISTRIBUTION</span><h2>Exposure Map</h2><div className="risk-ring"><div className="risk-ring-inner"><strong>{overallScore == null ? "—" : Math.round(overallScore)}</strong><span>RISK INDEX</span></div></div><div className="distribution-list">{distribution.map((item) => <div className="distribution-row" key={item.label}><div><span className={`distribution-dot ${item.label.toLowerCase()}`} /><span>{item.label}</span></div><strong>{item.value}</strong></div>)}</div><div className="risk-insight"><AlertTriangle size={17} /><div><strong>{analysisState?.status === "RISK_ANALYZED" ? "Explainable calculation" : "Risk analysis"}</strong><p>{typeof investigationSummary?.risk_model === "string" ? `Model ${investigationSummary.risk_model}; levels use documented score thresholds.` : "Risk records come from persisted backend calculations and explicitly labeled demo fixtures."}</p></div></div></aside></div>
    {selected && <RiskDetail risk={selected} onClose={() => setSelected(null)} />}
  </div>;
}

function SummaryCard({ label, value, suffix, icon, description, danger }: { label: string; value: string; suffix?: string; icon: ReactNode; description: string; danger?: boolean }) { return <div className={`summary-card glass-panel ${danger ? "danger" : ""}`}><div className="summary-top"><span>{label}</span><div className="summary-icon">{icon}</div></div><div className="summary-value">{value}{suffix && <small>{suffix}</small>}</div><p>{description}</p></div>; }
function RiskBadge({ level }: { level: RiskLevel }) { return <span className={`risk-level ${level.toLowerCase()}`}><span />{level}</span>; }
function RiskDetail({ risk, onClose }: { risk: RiskItem; onClose: () => void }) {
  return <div className="risk-overlay" onClick={onClose}><aside className="risk-drawer" onClick={(event) => event.stopPropagation()}><div className="drawer-header"><div><span className="risk-kicker">{risk.demo_mode ? "DEMO FIXTURE" : "CALCULATED RISK"}</span><h2>{risk.entity}</h2></div><button onClick={onClose} aria-label="Close risk details"><X size={17} /></button></div><RiskBadge level={risk.levelLabel} /><div className="drawer-score"><div><span>Risk score</span><strong>{risk.score === null ? "UNKNOWN" : `${Math.round(risk.score)}/100`}</strong></div><div className="large-score-track"><div className={`score-fill ${risk.levelLabel.toLowerCase()}`} style={{ width: `${Math.max(0, Math.min(100, risk.score ?? 0))}%` }} /></div></div><section className="drawer-section"><span className="risk-kicker">EXPLANATION</span><p className="drawer-reason">{risk.reason}</p></section>{risk.propagated_score !== null && risk.propagated_score !== undefined && <section className="drawer-section"><span className="risk-kicker">PROPAGATED EXPOSURE</span><p>{risk.propagated_score}/100 additional downstream contribution</p></section>}<section className="drawer-section"><span className="risk-kicker">RISK FACTORS</span>{risk.risk_factors?.map((factor) => <RiskFactorView factor={factor} key={factor.key} />) ?? <p>No factor breakdown was saved.</p>}</section><section className="drawer-section"><span className="risk-kicker">ENTITY TYPE</span><div className="affected-card"><Package size={18} /><strong>{risk.type}</strong><ChevronRight size={15} /></div></section><section className="drawer-section"><span className="risk-kicker">RECORDED</span><p>{new Date(risk.created_at).toLocaleString()}</p></section></aside></div>;
}
function RiskFactorView({ factor }: { factor: RiskFactor }) { return <div className="risk-factor-view"><div><strong>{factor.label}</strong><span>{factor.status === "UNKNOWN" || factor.score === null ? "UNKNOWN" : `${factor.score}/100`}</span></div><p>{factor.explanation}</p>{factor.source && <small>Source: {factor.source}</small>}</div>; }
function getRiskIcon(type: string) { if (type.toLowerCase().includes("region")) return <Globe2 size={18} />; if (type.toLowerCase().includes("facility")) return <Factory size={18} />; return <Package size={18} />; }
function normalizeLevel(value: string): RiskLevel { const normalized = value.toUpperCase(); if (normalized === "UNKNOWN") return "Unknown"; return levels.find((item) => item.toUpperCase() === normalized) ?? "Unknown"; }
function asNumber(value: unknown): number | null { return typeof value === "number" && Number.isFinite(value) ? value : null; }
export default RiskIntelligence;
