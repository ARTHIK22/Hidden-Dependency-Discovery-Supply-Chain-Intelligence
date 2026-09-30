import { useEffect, useState } from "react";
import { ArrowRight, ArrowUpRight, Database, Network, Search, ShieldCheck, Sparkles } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import Button from "../../components/ui/Button/Button";
import Card from "../../components/ui/Card/Card";
import Badge from "../../components/ui/Badge/Badge";
import PageContainer from "../../components/layout/PageContainer";
import { listInvestigations } from "../../features/investigations/investigation.api";
import { listEntities } from "../../features/entities/entity.api";
import { listRelationships } from "../../features/relationships/relationship.api";
import { listSources } from "../../features/sources/source.api";
import { getRiskAnalysis } from "../../features/risks/risk.api";
import { userMessage } from "../../services/api/errors";
import type { Investigation } from "../../types/investigation.types";
import type { RiskAnalysis } from "../../types/risk.types";
import "./dashboard.css";

function Overview() {
  const navigate = useNavigate();
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [counts, setCounts] = useState({ entities: 0, relationships: 0, sources: 0 });
  const [risk, setRisk] = useState<RiskAnalysis | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    Promise.all([listInvestigations({ limit: 100 }), listEntities({ limit: 100 }), listRelationships({ limit: 100 }), listSources({ limit: 100 }), getRiskAnalysis()])
      .then(([investigationRows, entityRows, relationshipRows, sourceRows, riskResult]) => {
        if (!active) return;
        setInvestigations(investigationRows);
        setCounts({ entities: entityRows.length, relationships: relationshipRows.length, sources: sourceRows.length });
        setRisk(riskResult);
      })
      .catch((reason) => { if (active) setError(userMessage(reason)); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, []);

  const stats = [
    { label: "Investigations", value: investigations.length, icon: Search },
    { label: "Entities in sample", value: counts.entities, icon: Database },
    { label: "Relationships in sample", value: counts.relationships, icon: Network },
    { label: "Sources in sample", value: counts.sources, icon: ShieldCheck },
  ];
  return <PageContainer><div className="dashboard animate-fade">
    <section className="dashboard-hero glass"><div className="hero-content"><div className="hero-label"><Sparkles size={14} />RECORDED SUPPLY INTELLIGENCE</div><h2>Understand your<br />recorded dependencies.</h2><p>Review stored entities, evidence and relationship structure. External research is not currently configured.</p><div className="hero-actions"><Button size="lg" onClick={() => navigate("/investigations/new")}><Search size={17} />Start Investigation<ArrowUpRight size={16} /></Button><Button variant="secondary" size="lg" onClick={() => navigate("/graph")}><Network size={16} />Explore Graph</Button></div></div></section>
    {error && <div role="alert" className="dashboard-error">{error} <button type="button" onClick={() => window.location.reload()}>Retry</button></div>}
    {busy ? <p aria-live="polite">Loading dashboard data…</p> : <>
      <section className="stats-grid">{stats.map(({ label, value, icon: Icon }) => <Card key={label} hover className="stat-card"><div className="stat-icon"><Icon size={18} /></div><div className="stat-content"><span>{label}</span><strong>{value}</strong><small>{label.includes("sample") ? "First record checked" : "Your account"}</small></div></Card>)}</section>
      <section className="dashboard-grid"><Card className="investigations-card"><SectionHeading eyebrow="WORKSPACE" title="Recent Investigations" action="View all" onAction={() => navigate("/investigations")} />{investigations.length === 0 ? <p>No investigations yet. <Link to="/investigations/new">Create your first investigation.</Link></p> : <div className="investigation-list">{investigations.slice(0, 5).map((item) => <button className="investigation-row" key={item.id} onClick={() => navigate(`/investigations/${item.id}`)}><div className="investigation-icon"><Network size={16} /></div><div className="investigation-info"><strong>{item.name}</strong><span>{item.target || item.description || "No description"}</span></div><div className="investigation-meta"><Badge variant={item.status === "completed" ? "success" : item.status === "running" ? "warning" : "default"}>{item.status}</Badge><small>{new Date(item.updated_at).toLocaleString()}</small></div></button>)}</div>}</Card>
        <Card className="risk-card"><SectionHeading eyebrow="INTELLIGENCE" title="Recorded Risk Signals" icon={<ShieldCheck size={19} className="section-icon" />} />{risk ? <><div className="risk-score"><div className="risk-number">{risk.risks.length}</div><div className="risk-score-info"><strong>Risk signals</strong><span>Derived from stored relationships</span></div></div><div className="risk-items">{risk.risks.slice(0, 5).map((item, index) => <RiskItem key={`${item.category}-${item.entity_id}-${index}`} label={item.category.split("_").join(" ")} value={item.severity} severity={item.severity === "high" ? "danger" : "warning"} />)}</div><Link to="/risks">Review risk analysis <ArrowRight size={14} /></Link></> : <p>Risk analysis unavailable.</p>}</Card></section>
    </>}
  </div></PageContainer>;
}

function SectionHeading({ eyebrow, title, action, icon, onAction }: { eyebrow: string; title: string; action?: string; icon?: React.ReactNode; onAction?: () => void }) { return <div className="section-heading"><div><span className="eyebrow">{eyebrow}</span><h3>{title}</h3></div>{action ? <button className="text-button" type="button" onClick={onAction}>{action}<ArrowUpRight size={14} /></button> : icon}</div>; }
function RiskItem({ label, value, severity }: { label: string; value: string; severity: "danger" | "warning" }) { return <div className="risk-item"><span>{label.split("_").join(" ")}</span><strong className={`risk-${severity}`}>{value}</strong></div>; }
export default Overview;
